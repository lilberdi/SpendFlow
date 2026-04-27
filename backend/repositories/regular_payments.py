from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import RegularPaymentModel
from backend.schemas.payment import RegularPaymentCreate


class RegularPaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[RegularPaymentModel]:
        stmt = select(RegularPaymentModel).order_by(RegularPaymentModel.category_name, RegularPaymentModel.name)
        return list(self.db.scalars(stmt))

    def get(self, payment_id: int) -> RegularPaymentModel | None:
        return self.db.get(RegularPaymentModel, payment_id)

    def create(self, payload: RegularPaymentCreate) -> RegularPaymentModel:
        row = RegularPaymentModel(
            name=payload.name.strip(),
            amount=float(payload.amount),
            category_name=payload.category_name.strip(),
            periodicity=payload.periodicity.strip().lower(),
            next_charge_at=payload.next_charge_at,
            last_paid_at=None,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def save(self, row: RegularPaymentModel) -> RegularPaymentModel:
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
