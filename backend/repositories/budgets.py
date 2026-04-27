from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import BudgetModel, TransactionModel
from backend.schemas.budget import BudgetCreate


class BudgetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert(self, payload: BudgetCreate) -> BudgetModel:
        stmt = select(BudgetModel).where(
            BudgetModel.category_name == payload.category_name.strip(),
            BudgetModel.month == payload.month,
            BudgetModel.year == payload.year,
        )
        existing = self.db.scalar(stmt)
        if existing:
            existing.limit_amount = float(payload.limit_amount)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        row = BudgetModel(
            category_name=payload.category_name.strip(),
            limit_amount=float(payload.limit_amount),
            month=payload.month,
            year=payload.year,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list(self, month: int | None = None, year: int | None = None) -> list[BudgetModel]:
        stmt = select(BudgetModel)
        if month is not None:
            stmt = stmt.where(BudgetModel.month == month)
        if year is not None:
            stmt = stmt.where(BudgetModel.year == year)
        stmt = stmt.order_by(BudgetModel.year.desc(), BudgetModel.month.desc(), BudgetModel.category_name.asc())
        return list(self.db.scalars(stmt))

    def get_for_period(self, category_name: str, month: int, year: int) -> BudgetModel | None:
        stmt = select(BudgetModel).where(
            BudgetModel.category_name == category_name,
            BudgetModel.month == month,
            BudgetModel.year == year,
        )
        return self.db.scalar(stmt)

    def spent_for_period(self, category_name: str, month: int, year: int) -> float:
        stmt = select(
            func.coalesce(func.sum(TransactionModel.amount), 0.0)
        ).where(
            TransactionModel.category == category_name,
            func.extract('month', TransactionModel.created_at) == month,
            func.extract('year', TransactionModel.created_at) == year,
        )
        value = self.db.scalar(stmt)
        return float(value or 0.0)
