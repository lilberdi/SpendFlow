from datetime import datetime

from pydantic import BaseModel, Field


class RegularPaymentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    amount: float = Field(gt=0)
    category_name: str = Field(min_length=1, max_length=64)
    periodicity: str = Field(description='monthly | weekly | yearly')
    next_charge_at: datetime | None = None


class UpcomingPaymentRead(BaseModel):
    """Карточка предстоящего регулярного платежа с привязкой к лимиту категории."""

    regular_payment_id: int
    name: str
    category_name: str
    periodicity: str
    planned_amount: float
    spent_amount: float
    pay_now_amount: float
    next_charge_at: datetime
    overspend_risk: bool
