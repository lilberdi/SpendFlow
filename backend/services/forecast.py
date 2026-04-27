from datetime import date

import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import TransactionModel


def _get_monthly_history(db: Session) -> list[tuple[str, float]]:
    stmt = (
        select(
            func.to_char(func.date_trunc('month', TransactionModel.created_at), 'YYYY-MM').label('month_key'),
            func.coalesce(func.sum(TransactionModel.amount), 0.0).label('total_amount'),
        )
        .group_by('month_key')
        .order_by('month_key')
    )
    rows = db.execute(stmt).all()
    return [(str(month_key), float(total_amount)) for month_key, total_amount in rows]


def forecast_next_month(total_limit: float, db: Session) -> tuple[float, dict]:
    history = _get_monthly_history(db)
    if not history:
        return 0.0, {
            'months': ['M1', 'M2'],
            'actual': [0.0],
            'forecast': 0.0,
            'limit': total_limit,
            'message': 'Недостаточно данных: в истории нет транзакций.',
        }

    y = np.array([amount for _, amount in history], dtype=float)
    months = [f'M{i + 1}' for i in range(len(history))]

    if len(history) < 2:
        # Fallback: для 1 месяца обучения регрессии недостаточно.
        fallback = float(y.mean())
        return fallback, {
            'months': [*months, f'M{len(history) + 1}'],
            'actual': y.tolist(),
            'forecast': fallback,
            'limit': total_limit,
            'message': 'Недостаточно истории (<2 месяцев), использовано среднее значение.',
        }

    x = np.arange(len(history), dtype=float).reshape(-1, 1)
    model = LinearRegression().fit(x, y)
    forecast = max(0.0, float(model.predict([[len(history)]])[0]))

    return forecast, {
        'months': [*months, f'M{len(history) + 1}'],
        'actual': y.tolist(),
        'forecast': forecast,
        'limit': total_limit,
        'message': 'Прогноз рассчитан на основе транзакций из PostgreSQL.',
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
