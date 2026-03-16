# src/recommendations.py
"""
Умные рекомендации на основе текущих трат и лимитов.
"""
from typing import Dict, List


def get_smart_recommendations(
    current_total: float,
    total_limit: float,
    category_totals: Dict[str, float],
    category_limits: Dict[str, float],
    current_transaction_amount: float = 0,
    current_category: str = None,
) -> List[str]:
    """
    Генерирует список рекомендаций по бюджету.
    
    Args:
        current_total: текущая общая сумма трат (включая рассматриваемую)
        total_limit: общий лимит бюджета
        category_totals: {категория: текущая_сумма}
        category_limits: {категория: лимит}
        current_transaction_amount: сумма добавляемой траты
        current_category: категория добавляемой траты
    
    Returns:
        Список строк-рекомендаций
    """
    tips = []
    
    # Общий бюджет
    if total_limit > 0:
        usage_pct = current_total / total_limit * 100
        if usage_pct >= 100:
            tips.append("⚠️ Общий бюджет превышен. Рекомендуется приостановить траты до следующего месяца.")
        elif usage_pct >= 90:
            tips.append(f"Вы близки к общему лимиту ({usage_pct:.0f}%). Осталось {total_limit - current_total:,.0f} ₸.")
        elif usage_pct >= 80:
            tips.append(f"Использовано {usage_pct:.0f}% бюджета. Следите за расходами.")
    
    # По категориям
    for cat, limit in category_limits.items():
        spent = category_totals.get(cat, 0)
        if limit <= 0:
            continue
        pct = spent / limit * 100
        if pct >= 100:
            tips.append(f"Категория «{cat}»: лимит превышен. Рекомендуется сократить траты в этой категории.")
        elif pct >= 80:
            tips.append(f"Категория «{cat}»: использовано {pct:.0f}%. Осталось {limit - spent:,.0f} ₸.")
    
    # Текущая трата
    if current_transaction_amount > 0 and current_category and current_category in category_limits:
        limit = category_limits[current_category]
        current_cat_total = category_totals.get(current_category, 0)
        after = current_cat_total + current_transaction_amount
        if after > limit:
            tips.append(f"Эта трата ({current_transaction_amount:,.0f} ₸) превысит лимит категории «{current_category}».")
    
    if not tips:
        tips.append("Бюджет в порядке. Продолжайте в том же духе.")
    
    return tips
