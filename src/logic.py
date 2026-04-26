import json
import os
from typing import Any, Dict, List, Optional

# Автоматическое определение пути к файлу
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_PATH = os.path.join(BASE_DIR, 'data', 'raw', 'rules.json')


def load_rules():
    """Загружает правила из JSON файла."""
    with open(RULES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_rules(data):
    """
    Принимает словарь данных транзакции (data), возвращает строковый вердикт.
    
    Args:
        data: словарь с полями:
            - description: описание траты
            - amount: сумма траты
            - category: категория траты
            - tags_list: список тегов
            - is_budget_exceeded: флаг превышения общего бюджета
            - category_total: текущая сумма трат по категории
    
    Returns:
        str: вердикт о соответствии правилам
    """
    rules = load_rules()
    
    # --- 1. HARD FILTERS (Критические проверки) ---
    
    # Проверка: если общий бюджет уже превышен, блокируем новую трату
    if rules['critical_rules']['block_if_budget_exceeded'] and data.get('is_budget_exceeded', False):
        return "⛔️ Критическая ошибка: Общий бюджет уже превышен. Новая трата заблокирована."
    
    # Проверка: сумма траты должна быть положительной
    if data['amount'] < rules['thresholds']['min_amount']:
        return "⛔️ Критическая ошибка: Сумма траты не может быть отрицательной"
    
    # Проверка на запрещенные элементы в тегах (Blacklist)
    for tag in data.get('tags_list', []):
        if tag in rules['lists']['blacklist']:
            return f"⛔️ Критическая ошибка: Найден запрещенный тег ({tag})"
    
    # --- 2. БИЗНЕС-ЛОГИКА (Сравнение с лимитами) ---
    
    # Проверка превышения общего бюджета
    if rules['critical_rules']['must_not_exceed_total_budget']:
        # Предполагаем, что data содержит текущую сумму всех трат
        current_total = data.get('total_spent', 0) + data['amount']
        if current_total > rules['thresholds']['max_total_budget']:
            return f"❌ Отказ: Превышен общий лимит бюджета ({rules['thresholds']['max_total_budget']}). Текущая сумма: {current_total}"
    
    # Проверка превышения лимита по категории
    if rules['critical_rules']['must_not_exceed_category_budget']:
        category = data.get('category', 'Other')
        category_limits = rules['thresholds']['max_category_budget']
        
        if category in category_limits:
            # Проверяем, не превысит ли новая трата лимит категории
            new_category_total = data.get('category_total', 0) + data['amount']
            category_limit = category_limits[category]
            
            if new_category_total > category_limit:
                return (
                    f"❌ Отказ: Превышен лимит категории '{category}' ({category_limit}). "
                    f"Текущая сумма по категории: {data.get('category_total', 0)}, "
                    f"новая трата: {data['amount']}, итого: {new_category_total}"
                )
            
            # Предупреждение при приближении к лимиту (80% от лимита)
            if new_category_total >= category_limit * 0.8:
                return (
                    f"⚠️ Предупреждение: Приближение к лимиту категории '{category}'. "
                    f"Использовано {new_category_total} из {category_limit} "
                    f"({int(new_category_total / category_limit * 100)}%)"
                )
    
    # Проверка на наличие элементов из whitelist (опционально)
    has_whitelist_tag = any(tag in rules['lists']['whitelist'] for tag in data.get('tags_list', []))
    
    # Если все проверки пройдены
    success_msg = "✅ Успех: Трата соответствует правилам контроля бюджета"
    if has_whitelist_tag:
        success_msg += " (найден подтвержденный тег)"
    
    return success_msg


def process_text_message(text: str, data_source: Any, context: dict = None) -> str:
    """
    «Мозг» чатбота: поиск в графе знаний и умные рекомендации по бюджету.
    
    context: опционально — текущие траты и лимиты для рекомендаций.
    """
    if text is None:
        return "Я не понял сообщение."
    
    original_text = text.strip()
    query = original_text.lower()
    
    # Умные рекомендации (если запросили и есть контекст)
    if context and any(
        word in query
        for word in [
            "бюджет", "рекомендации", "советы", "как дела", "совет",
            "лимит", "перерасход", "помощь", "что делать",
        ]
    ):
        try:
            from recommendations import get_smart_recommendations
            tips = get_smart_recommendations(
                current_total=context.get("current_total", 0),
                total_limit=context.get("total_limit", 10000),
                category_totals=context.get("category_totals", {}),
                category_limits=context.get("category_limits", {}),
                current_transaction_amount=context.get("amount", 0),
                current_category=context.get("category"),
            )
            return "**Рекомендации по бюджету:**\n\n" + "\n\n".join(f"• {t}" for t in tips)
        except Exception:
            pass
    
    # Приветствие
    if any(word in query for word in ["привет", "hello", "hi"]):
        return (
            "Привет! Я SpendFlow-бот по учету расходов. "
            "Напиши название магазина (например, 'Uber' или 'Starbucks'), "
            "категории ('Transport', 'Food') или спроси про **бюджет** и **рекомендации**."
        )
    
    # Работа с графом знаний (NetworkX Graph из Lab 3)
    # Ищем узел без учета регистра
    if hasattr(data_source, "nodes"):
        node_map = {str(node).lower(): node for node in data_source.nodes}
        if query in node_map:
            node = node_map[query]
            neighbors = list(data_source.neighbors(node))
            if neighbors:
                neighbors_str = ", ".join(str(n) for n in neighbors)
                return f"Я нашёл '{node}' в графе знаний. С этим связано: {neighbors_str}."
            return f"Я нашёл '{node}' в графе знаний, но у него пока нет связей."
    
    # Если ничего не нашли
    return (
        "Я не знаю такого термина. "
        "Попробуйте ввести точное название магазина или категории "
        "(например, 'Uber', 'Starbucks' или 'Transport')."
    )

