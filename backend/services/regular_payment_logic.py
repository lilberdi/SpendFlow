"""Расчёт суммы «к оплате» и сдвига даты для регулярных платежей."""

from __future__ import annotations

from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta

_PERIOD_DELTA: dict[str, relativedelta] = {
    'monthly': relativedelta(months=1),
    'weekly': relativedelta(weeks=1),
    'yearly': relativedelta(years=1),
}


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_pay_now_amount(
    *,
    amount: float,
    periodicity: str,
    last_paid_at: datetime | None,
    now: datetime,
) -> float:
    """Один платёж за период (календарный месяц / ISO-неделя / год)."""
    now_u = _utc(now)
    if last_paid_at is None:
        return round(float(amount), 2)
    last = _utc(last_paid_at)
    per = (periodicity or 'monthly').lower()
    if per == 'monthly':
        if (last.year, last.month) == (now_u.year, now_u.month):
            return 0.0
    elif per == 'weekly':
        lwi = last.date().isocalendar()
        nwi = now_u.date().isocalendar()
        if (lwi.year, lwi.week) == (nwi.year, nwi.week):
            return 0.0
    elif per == 'yearly':
        if last.year == now_u.year:
            return 0.0
    else:
        if (last.year, last.month) == (now_u.year, now_u.month):
            return 0.0
    return round(float(amount), 2)


def advance_next_charge(next_charge_at: datetime, periodicity: str) -> datetime:
    delta = _PERIOD_DELTA.get((periodicity or 'monthly').lower(), relativedelta(months=1))
    base = _utc(next_charge_at)
    return base + delta
