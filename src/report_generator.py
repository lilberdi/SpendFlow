# src/report_generator.py
"""
Генерация текстового отчёта «Итоги недели/месяца».
"""
from typing import Dict, List


def generate_weekly_report(
    daily_amounts: List[float],
    day_names: List[str] = None,
) -> str:
    """
    Генерирует текстовый отчёт за неделю.
    
    Args:
        daily_amounts: список сумм по дням [Пн, Вт, ..., Вс]
        day_names: названия дней (по умолчанию Пн..Вс)
    """
    day_names = day_names or ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    total = sum(daily_amounts)
    
    if total == 0:
        return "За неделю расходов не было."
    
    # Самый затратный день
    max_idx = max(range(len(daily_amounts)), key=lambda i: daily_amounts[i])
    max_day = day_names[max_idx] if max_idx < len(day_names) else f"День {max_idx+1}"
    max_amount = daily_amounts[max_idx]
    
    # Средний расход в день
    avg_daily = total / 7
    
    report = (
        f"**Итоги недели:** За 7 дней потрачено **{total:,.0f}** ₸. "
        f"Средний расход в день: **{avg_daily:,.0f}** ₸. "
        f"Самый затратный день — **{max_day}** ({max_amount:,.0f} ₸)."
    )
    return report


def generate_monthly_summary(
    category_totals: Dict[str, float],
    total_spent: float,
    total_limit: float,
) -> str:
    """
    Генерирует итоговый отчёт за месяц по категориям.
    """
    if total_spent <= 0:
        return "За месяц расходов пока нет."
    
    # Топ-3 категории по доле
    sorted_cats = sorted(
        category_totals.items(),
        key=lambda x: x[1],
        reverse=True,
    )[:3]
    
    parts = []
    for cat, amount in sorted_cats:
        pct = amount / total_spent * 100 if total_spent else 0
        parts.append(f"{cat} — {pct:.0f}% ({amount:,.0f} ₸)")
    
    budget_pct = (total_spent / total_limit * 100) if total_limit else 0
    status = "в пределах лимита" if total_spent <= total_limit else "превышен"
    
    report = (
        f"**Итоги месяца:** Всего потрачено **{total_spent:,.0f}** ₸ "
        f"(лимит {total_limit:,.0f} ₸, использование {budget_pct:.0f}% — {status}). "
        f"Основные категории: {', '.join(parts)}."
    )
    return report
