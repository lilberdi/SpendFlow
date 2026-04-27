from __future__ import annotations

from pydantic import BaseModel, Field

from backend.schemas.budget import BudgetRead
from backend.schemas.transaction import TransactionRead


class DashboardResponse(BaseModel):
    month_total: float
    forecast: float
    total_limit: float
    remaining: float
    anomalies_this_month: int
    chart_months: list[str]
    #: Monthly expense / outflow (fact + forecast point), same length as chart_months
    chart_expense_amounts: list[float]
    #: True для столбца прогноза (последний период), иначе факт
    chart_expense_forecast_flags: list[bool] = Field(default_factory=list)
    forecast_note: str | None = None
    budgets: list[BudgetRead]
    recent_transactions: list[TransactionRead]
    anomaly_ids: list[int] = Field(default_factory=list)
