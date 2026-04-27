from datetime import datetime

from sqlalchemy import delete, func, select, or_
from sqlalchemy.orm import Session

from backend.db.models import TransactionModel
from backend.schemas.transaction import TransactionCreate, TransactionUpdate


class TransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: TransactionCreate) -> TransactionModel:
        row = TransactionModel(
            description=payload.description.strip(),
            amount=float(payload.amount),
            category=payload.category.strip(),
            tags=', '.join(payload.tags) if payload.tags else '',
            source=payload.source,
            ocr_merchant_raw=payload.ocr_merchant_raw,
            ocr_raw_text=payload.ocr_raw_text,
            ocr_confidence=payload.ocr_confidence,
            receipt_storage_key=payload.receipt_storage_key,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get(self, transaction_id: int) -> TransactionModel | None:
        return self.db.get(TransactionModel, transaction_id)

    def _filters(
        self,
        category: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        amount_min: float | None = None,
        amount_max: float | None = None,
        search: str | None = None,
    ):
        clauses = []
        if category:
            clauses.append(TransactionModel.category == category)
        if date_from:
            clauses.append(TransactionModel.created_at >= date_from)
        if date_to:
            clauses.append(TransactionModel.created_at <= date_to)
        if amount_min is not None:
            clauses.append(TransactionModel.amount >= amount_min)
        if amount_max is not None:
            clauses.append(TransactionModel.amount <= amount_max)
        if search and search.strip():
            term = f'%{search.strip()}%'
            clauses.append(
                or_(
                    TransactionModel.description.ilike(term),
                    TransactionModel.category.ilike(term),
                )
            )
        return clauses

    def count(
        self,
        category: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        amount_min: float | None = None,
        amount_max: float | None = None,
        search: str | None = None,
    ) -> int:
        stmt = select(func.count(TransactionModel.id))
        for c in self._filters(category, date_from, date_to, amount_min, amount_max, search):
            stmt = stmt.where(c)
        value = self.db.scalar(stmt)
        return int(value or 0)

    def list(
        self,
        limit: int = 200,
        offset: int = 0,
        category: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        amount_min: float | None = None,
        amount_max: float | None = None,
        search: str | None = None,
    ) -> list[TransactionModel]:
        stmt = select(TransactionModel)
        for c in self._filters(category, date_from, date_to, amount_min, amount_max, search):
            stmt = stmt.where(c)

        stmt = (
            stmt.order_by(TransactionModel.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
        )
        return list(self.db.scalars(stmt))

    def sum(
        self,
        category: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        amount_min: float | None = None,
        amount_max: float | None = None,
    ) -> float:
        stmt = select(func.coalesce(func.sum(TransactionModel.amount), 0.0))
        if category:
            stmt = stmt.where(TransactionModel.category == category)
        if date_from:
            stmt = stmt.where(TransactionModel.created_at >= date_from)
        if date_to:
            stmt = stmt.where(TransactionModel.created_at <= date_to)
        if amount_min is not None:
            stmt = stmt.where(TransactionModel.amount >= amount_min)
        if amount_max is not None:
            stmt = stmt.where(TransactionModel.amount <= amount_max)
        value = self.db.scalar(stmt)
        return float(value or 0.0)

    def update(self, transaction_id: int, payload: TransactionUpdate) -> TransactionModel | None:
        row = self.get(transaction_id)
        if row is None:
            return None

        if payload.description is not None:
            row.description = payload.description.strip()
        if payload.amount is not None:
            row.amount = float(payload.amount)
        if payload.category is not None:
            row.category = payload.category.strip()
        if payload.tags is not None:
            row.tags = ', '.join(payload.tags) if payload.tags else ''

        self.db.commit()
        self.db.refresh(row)
        return row

    def delete(self, transaction_id: int) -> bool:
        stmt = delete(TransactionModel).where(TransactionModel.id == transaction_id)
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0
