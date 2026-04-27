from datetime import datetime, timezone

import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import TransactionModel

# Короткие названия месяцев для подписей графика (например «Апр 2026»)
_MONTH_SHORT_RU = (
    'янв.',
    'фев.',
    'мар.',
    'апр.',
    'мая',
    'июн.',
    'июл.',
    'авг.',
    'сен.',
    'окт.',
    'ноя.',
    'дек.',
)


def _format_ym_ru(ym: str) -> str:
    y, m = map(int, ym.split('-'))
    raw = _MONTH_SHORT_RU[m - 1]
    word = raw.rstrip('.').capitalize()
    return f'{word} {y}'


def _add_months_to_key(ym: str, delta: int) -> str:
    y, month = map(int, ym.split('-'))
    month += delta
    while month > 12:
        month -= 12
        y += 1
    while month < 1:
        month += 12
        y -= 1
    return f'{y:04d}-{month:02d}'


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
    """
    Возвращает прогноз и данные для графика.
    Подписи месяцев — по реальным периодам из БД (YYYY-MM → «Апр 2026»).
    Последний столбец — прогноз на следующий месяц (expense_is_forecast[-1] == True).
    """
    now = datetime.now(timezone.utc)
    history = _get_monthly_history(db)
    if not history:
        curr_key = f'{now.year:04d}-{now.month:02d}'
        prev_key = _add_months_to_key(curr_key, -1)
        month_keys = [prev_key, curr_key]
        labels = [_format_ym_ru(k) for k in month_keys]
        return 0.0, {
            'months': labels,
            'actual': [0.0],
            'forecast': 0.0,
            'limit': total_limit,
            'message': 'Недостаточно данных: в истории нет транзакций.',
            'expense_is_forecast': [False, True],
        }

    y = np.array([amount for _, amount in history], dtype=float)
    month_keys_hist = [mk for mk, _ in history]
    forecast_month_key = _add_months_to_key(month_keys_hist[-1], 1)
    month_keys = [*month_keys_hist, forecast_month_key]
    labels = [_format_ym_ru(k) for k in month_keys]
    expense_is_forecast = [False] * len(history) + [True]

    if len(history) < 2:
        fallback = float(y.mean())
        return fallback, {
            'months': labels,
            'actual': y.tolist(),
            'forecast': fallback,
            'limit': total_limit,
            'message': 'Недостаточно истории (<2 месяцев), использовано среднее значение.',
            'expense_is_forecast': expense_is_forecast,
        }

    x = np.arange(len(history), dtype=float).reshape(-1, 1)
    model = LinearRegression().fit(x, y)
    forecast = max(0.0, float(model.predict([[len(history)]])[0]))

    return forecast, {
        'months': labels,
        'actual': y.tolist(),
        'forecast': forecast,
        'limit': total_limit,
        'message': 'Прогноз рассчитан на основе транзакций из PostgreSQL.',
        'expense_is_forecast': expense_is_forecast,
    }


def budget_success_probability(
    total_spent: float,
    total_limit: float,
    day_of_month: int | None = None,
    days_in_month: int = 30,
) -> tuple[float, str]:
    if total_limit <= 0:
        return 50.0, 'Лимит не задан'

    today = datetime.now(timezone.utc).date()
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
