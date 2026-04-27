from datetime import date

import numpy as np
from sklearn.linear_model import LinearRegression


def _get_synthetic_monthly_data() -> list[tuple[int, float]]:
    np.random.seed(42)
    base = 75000
    months = list(range(6))
    amounts = [base + np.random.randint(-8000, 12000) for _ in months]
    return list(zip(months, amounts))


def forecast_next_month(total_limit: float) -> tuple[float, dict]:
    data = _get_synthetic_monthly_data()
    x = np.array([[m] for m, _ in data])
    y = np.array([a for _, a in data])

    model = LinearRegression().fit(x, y)
    forecast = max(0.0, float(model.predict([[len(data)]])[0]))

    return forecast, {
        'months': [f'М{i + 1}' for i in range(len(data) + 1)],
        'actual': [a for _, a in data],
        'forecast': forecast,
        'limit': total_limit,
    }


def budget_success_probability(
    total_spent: float,
    total_limit: float,
    day_of_month: int | None = None,
    days_in_month: int = 30,
) -> tuple[float, str]:
    if total_limit <= 0:
        return 50.0, 'Лимит не задан'

    today = date.today()
    day_of_month = day_of_month or today.day

    if day_of_month <= 1:
        return 80.0, 'Начало месяца — данных мало для точной оценки'

    daily_rate = total_spent / day_of_month
    projected_total = daily_rate * days_in_month

    if projected_total <= total_limit:
        buffer = total_limit - projected_total
        prob = min(95.0, 70.0 + buffer / total_limit * 25)
        return round(prob, 1), (
            f'При текущем темпе ({daily_rate:,.0f} ₸/день) прогноз на конец месяца: '
            f'{projected_total:,.0f} ₸. В укладку.'
        )

    over = projected_total - total_limit
    prob = max(5.0, 50.0 - over / total_limit * 40)
    return round(prob, 1), (
        f'При текущем темпе ({daily_rate:,.0f} ₸/день) прогноз: {projected_total:,.0f} ₸, '
        f'превышение ~{over:,.0f} ₸. Рекомендуется сократить траты.'
    )
