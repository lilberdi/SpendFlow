from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class TransactionModel(Base):
    __tablename__ = 'transactions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tags: Mapped[str] = mapped_column(String(255), default='', nullable=False)
    source: Mapped[str] = mapped_column(String(16), default='manual', nullable=False)
    ocr_merchant_raw: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    receipt_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)


class RegularPaymentModel(Base):
    __tablename__ = 'regular_payments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    category_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    periodicity: Mapped[str] = mapped_column(String(16), nullable=False, default='monthly')
    next_charge_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BudgetModel(Base):
    __tablename__ = 'budgets'
    __table_args__ = (UniqueConstraint('category_name', 'month', 'year', name='uq_budget_category_month_year'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    limit_amount: Mapped[float] = mapped_column(Float, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
