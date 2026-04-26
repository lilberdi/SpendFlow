# src/forecast.py
"""
Прогноз расходов (Time Series) и оценка вероятности уложиться в бюджет.
"""
from datetime import date
from typing import Dict, List, Tuple

import numpy as np
from sklearn.linear_model import LinearRegression


def _get_synthetic_monthly_data() -> List[Tuple[int, float]]:
    """
    Имитационные ежемесячные данные за последние 6 месяцев.
    Возвращает список (месяц_индекс, сумма_расходов).
    """
    np.random.seed(42)
    base = 75000
    months = list(range(6))
    amounts = [base + np.random.randint(-8000, 12000) for _ in months]
    return list(zip(months, amounts))


def forecast_next_month(total_limit: float) -> Tuple[float, Dict]:
    """
    Прогноз общей суммы расходов на следующий месяц.
    
    Returns:
        (прогноз_в_тенге, данные_для_графика)
    """
    data = _get_synthetic_monthly_data()
    X = np.array([[m] for m, _ in data])
    y = np.array([a for _, a in data])
    
    model = LinearRegression().fit(X, y)
    next_month_idx = len(data)
    forecast = model.predict([[next_month_idx]])[0]
    forecast = max(0, float(forecast))
    
    chart_data = {
        "months": [f"М{i+1}" for i in range(len(data) + 1)],
        "actual": [a for _, a in data],
        "forecast": float(forecast),
        "limit": total_limit,
    }
    return forecast, chart_data


def budget_success_probability(
    total_spent: float,
    total_limit: float,
    day_of_month: int = None,
    days_in_month: int = 30,
) -> Tuple[float, str]:
    """
    Оценка вероятности уложиться в бюджет до конца месяца.
    На основе текущего темпа трат экстраполируем на оставшиеся дни.
    
    Returns:
        (вероятность 0..100, пояснение)
    """
    if total_limit <= 0:
        return 50.0, "Лимит не задан"
    
    today = date.today()
    day_of_month = day_of_month or today.day
    days_left = max(1, days_in_month - day_of_month)
    
    if day_of_month <= 1:
        return 80.0, "Начало месяца — данных мало для точной оценки"
    
    daily_rate = total_spent / day_of_month
    projected_total = daily_rate * days_in_month
    remaining_budget = max(0, total_limit - total_spent)
    
    if projected_total <= total_limit:
        # Укладываемся — вероятность высокая
        buffer = total_limit - projected_total
        prob = min(95, 70 + buffer / total_limit * 25)
        return round(prob, 1), (
            f"При текущем темпе ({daily_rate:,.0f} ₸/день) "
            f"прогноз на конец месяца: {projected_total:,.0f} ₸. "
            f"В укладку."
        )
    else:
        # Превышаем
        over = projected_total - total_limit
        prob = max(5, 50 - over / total_limit * 40)
        return round(prob, 1), (
            f"При текущем темпе ({daily_rate:,.0f} ₸/день) "
            f"прогноз: {projected_total:,.0f} ₸, превышение ~{over:,.0f} ₸. "
            f"Рекомендуется сократить траты."
        )
