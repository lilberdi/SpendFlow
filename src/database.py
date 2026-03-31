# -*- coding: utf-8 -*-
"""
Модуль персистентного хранения транзакций SpendFlow (SQLite).

Зачем этот слой:
----------------
Раньше все «траты» жили только в памяти Streamlit (поля сайдбара) и сбрасывались
при перезапуске приложения. SQLite — встроенная в Python файловая база: один файл
на диске, без отдельного сервера PostgreSQL. Это минимальный шаг к «настоящему»
продукту: история трат, основа для отчётов и обучения ML на реальных данных.

Почему SQLite, а не сразу PostgreSQL:
-------------------------------------
- Нулевая настройка: pip не нужен для драйвера (sqlite3 в стандартной библиотеке).
- Файл можно копировать/бэкапить целиком.
- Для одного пользователя и учебного проекта этого достаточно; позже схему
  можно перенести в PostgreSQL с теми же SQL-запросами почти без изменений.

Где лежит файл БД:
-----------------
Рядом с корнем проекта (родитель каталога `src/`), имя `spendflow.db`.
Путь вычисляется от расположения этого файла, чтобы приложение работало
независимо от текущей рабочей директории в терминале.

Потоки и Streamlit:
-------------------
Каждое действие пользователя перезапускает скрипт `main.py`. Мы открываем
соединение на время одной операции и сразу закрываем (`with sqlite3.connect`).
Так мы не держим «висящее» соединение между перезапусками и избегаем блокировок
файла на Windows/macOS при простых сценариях.

Схема таблицы `transactions`:
-----------------------------
- id            — суррогатный ключ (автоинкремент). Удобно для ссылок и удаления.
- created_at    — время записи в ISO-формате (UTC через datetime.utcnow().isoformat()).
                  Текстовый ISO упрощает сортировку ORDER BY без типа TIMESTAMP везде.
- description   — человекочитаемое описание (магазин, комментарий).
- amount        — сумма в тенге; CHECK (amount >= 0) отсекает отрицательные на уровне БД.
- category      — строка категории (как в rules.json / UI).
- tags          — теги одной строкой через запятую (проще, чем отдельная таблица
                  tag_transaction для учебного проекта; при росте — нормализовать).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Путь к файлу базы: каталог проекта = родитель `src/`
# ---------------------------------------------------------------------------
# __file__ указывает на .../SpendFlow/src/database.py
# dirname дважды поднимает на уровень SpendFlow/
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
DB_FILENAME = "spendflow.db"
DB_PATH = os.path.join(_PROJECT_ROOT, DB_FILENAME)


def get_db_path() -> str:
    """
    Возвращает абсолютный путь к файлу SQLite.

    Вынесено в функцию, чтобы тесты или скрипты миграции могли подменить путь
    без правки константы (в будущем можно добавить переменную окружения).
    """
    return DB_PATH


def init_db() -> None:
    """
    Создаёт файл БД (если его ещё нет) и таблицу `transactions`.

    Безопасно вызывать при каждом старте приложения: `CREATE TABLE IF NOT EXISTS`
    не затирает существующие данные.

    Почему отдельная функция, а не «ленивое» создание в add_transaction:
    - Явная точка инициализации в main.py читается как «здесь поднимается хранилище».
    - Сюда же позже можно добавить CREATE INDEX, миграции версий схемы и т.д.
    """
    # timeout=5 — если другой процесс держит файл, подождём чуть-чуть вместо мгновенного сбоя
    with sqlite3.connect(DB_PATH, timeout=5) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")  # при будущих FK — уже включено
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL CHECK (amount >= 0),
                category TEXT NOT NULL,
                tags TEXT
            );
            """
        )
        # Индекс ускоряет выборку «последних N записей» по времени
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transactions_created_at
            ON transactions (created_at DESC);
            """
        )
        conn.commit()


def add_transaction(
    description: str,
    amount: float,
    category: str,
    tags: Optional[List[str]] = None,
) -> int:
    """
    Вставляет одну транзакцию и возвращает её `id`.

    Параметры:
        description — что потратили (например, «Uber до офиса»).
        amount      — сумма в ₸; отрицательные значения лучше отсекать до вызова,
                      но CHECK в таблице всё равно защитит от ошибок.
        category    — одна из категорий бюджета (Transport, Food, ...).
        tags        — список тегов; в БД склеивается в строку через запятую,
                      чтобы не усложнять схему второй таблицей.

    Возвращает:
        INTEGER — первичный ключ новой строки (lastrowid).

    Исключения:
        sqlite3.IntegrityError — если нарушен CHECK (amount < 0) и т.п.
    """
    tags = tags or []
    tags_str = ", ".join(tags) if tags else ""

    # Время в UTC в ISO — однозначно при разборе и сортировке как строка
    created_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH, timeout=5) as conn:
        cur = conn.execute(
            """
            INSERT INTO transactions (created_at, description, amount, category, tags)
            VALUES (?, ?, ?, ?, ?);
            """,
            (created_at, description.strip(), float(amount), category.strip(), tags_str),
        )
        conn.commit()
        return int(cur.lastrowid)


def fetch_recent_transactions(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Возвращает последние `limit` транзакций от новых к старым.

    Формат строк — словари для удобной передачи в pandas.DataFrame или st.dataframe.

    Почему Dict, а не кортежи:
    - В UI и отчётах понятнее имена колонок без запоминания порядка полей.
    """
    limit = max(1, min(int(limit), 500))  # защита от случайного limit=10**9

    with sqlite3.connect(DB_PATH, timeout=5) as conn:
        conn.row_factory = sqlite3.Row  # доступ к колонкам по имени
        cur = conn.execute(
            """
            SELECT id, created_at, description, amount, category, tags
            FROM transactions
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (limit,),
        )
        rows = cur.fetchall()

    # Row → обычный dict для Streamlit / JSON-сериализации
    return [dict(r) for r in rows]


def sum_amounts_since(created_after_iso: Optional[str] = None) -> float:
    """
    Сумма всех amount (опционально только записей новее указанной даты ISO).

    Заготовка для будущих отчётов «сколько потрачено за месяц» без выгрузки
    всех строк в Python. Пока можно не вызывать из UI — но API уже есть.
    """
    with sqlite3.connect(DB_PATH, timeout=5) as conn:
        if created_after_iso:
            cur = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE created_at >= ?;",
                (created_after_iso,),
            )
        else:
            cur = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions;")
        row = cur.fetchone()
        return float(row[0] if row and row[0] is not None else 0.0)
