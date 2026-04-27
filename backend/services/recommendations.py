def get_smart_recommendations(
    current_total: float,
    total_limit: float,
    category_totals: dict[str, float],
    category_limits: dict[str, float],
    current_transaction_amount: float = 0,
    current_category: str | None = None,
) -> list[str]:
    tips: list[str] = []

    if total_limit > 0:
        usage_pct = current_total / total_limit * 100
        if usage_pct >= 100:
            tips.append('⚠️ Общий бюджет превышен. Рекомендуется приостановить траты до следующего месяца.')
        elif usage_pct >= 90:
            tips.append(f'Вы близки к общему лимиту ({usage_pct:.0f}%). Осталось {total_limit - current_total:,.0f} ₸.')
        elif usage_pct >= 80:
            tips.append(f'Использовано {usage_pct:.0f}% бюджета. Следите за расходами.')

    for cat, limit in category_limits.items():
        spent = category_totals.get(cat, 0)
        if limit <= 0:
            continue
        pct = spent / limit * 100
        if pct >= 100:
            tips.append(f"Категория «{cat}»: лимит превышен. Рекомендуется сократить траты в этой категории.")
        elif pct >= 80:
            tips.append(f"Категория «{cat}»: использовано {pct:.0f}%. Осталось {limit - spent:,.0f} ₸.")

    if current_transaction_amount > 0 and current_category and current_category in category_limits:
        limit = category_limits[current_category]
        current_cat_total = category_totals.get(current_category, 0)
        if current_cat_total + current_transaction_amount > limit:
            tips.append(f"Эта трата ({current_transaction_amount:,.0f} ₸) превысит лимит категории «{current_category}».")

    if not tips:
        tips.append('Бюджет в порядке. Продолжайте в том же духе.')

    return tips
