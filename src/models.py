# src/models.py
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date


@dataclass
class Store:
    """
    Магазин/Сервис, где была совершена транзакция.
    Примеры: Uber, Starbucks, Magnum, McDonald's
    """
    name: str                    # Уникальное название магазина (id)
    category: str                # Категория расходов (Transport, Food, Shopping и т.д.)
    attributes: List[str] = field(default_factory=list)  # Дополнительные свойства (tags, location)
    typical_amount: float = 0.0  # Типичная сумма транзакции в этом магазине
    
    def __str__(self):
        attrs = ', '.join(self.attributes) if self.attributes else 'нет атрибутов'
        return f"{self.name} → {self.category} ({attrs})"


@dataclass
class Category:
    """
    Категория расходов.
    Примеры: Transport, Food, Shopping, Entertainment
    """
    name: str                    # Название категории
    description: str = ""        # Описание категории
    budget_limit: float = 0.0    # Лимит бюджета для категории
    attributes: List[str] = field(default_factory=list)  # Связанные ключевые слова
    
    def __str__(self):
        return f"{self.name} (лимит: {self.budget_limit} ₸)"


@dataclass
class Transaction:
    """
    Транзакция/расход.
    Связывает магазин, категорию и сумму.
    """
    store_name: str              # Название магазина
    amount: float                 # Сумма транзакции
    category: str                 # Категория расходов
    date: Optional[date] = None   # Дата транзакции
    tags: List[str] = field(default_factory=list)  # Теги транзакции
    
    def __str__(self):
        date_str = self.date.strftime("%d.%m.%Y") if self.date else "без даты"
        return f"{self.store_name}: {self.amount} ₸ ({self.category}) - {date_str}"
