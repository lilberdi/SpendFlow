from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import TransactionModel


@dataclass
class ExpenseAnomalyDetector:
    model: IsolationForest | None
    category_to_id: dict[str, int]
    is_fallback: bool = False

    def score(self, amount: float, category: str) -> tuple[str, float]:
        if amount <= 0:
            return 'invalid', -1.0
        if self.model is None:
            return 'insufficient_data', 0.0
        cat_id = self.category_to_id.get(category, -1)
        x = np.array([[amount, float(cat_id)]])
        raw = float(self.model.decision_function(x)[0])
        if raw > 0.1:
            label = 'normal'
        elif raw > -0.2:
            label = 'warning'
        else:
            label = 'anomaly'
        return label, raw


def _training_rows_from_db(db: Session) -> tuple[np.ndarray, dict[str, int]]:
    db_rows = db.execute(select(TransactionModel.amount, TransactionModel.category)).all()
    if not db_rows:
        return np.empty((0, 2)), {}

    categories = sorted({str(category) for _, category in db_rows})
    category_to_id = {category: idx for idx, category in enumerate(categories)}

    features: list[list[float]] = []
    for amount, category in db_rows:
        features.append([float(amount), float(category_to_id[str(category)])])
    x = np.array(features, dtype=float)
    return x, category_to_id


def build_expense_anomaly_detector(db: Session) -> ExpenseAnomalyDetector:
    x, category_to_id = _training_rows_from_db(db)
    if x.shape[0] < 10:
        # IsolationForest на слишком малом объеме дает нестабильные результаты.
        return ExpenseAnomalyDetector(model=None, category_to_id=category_to_id, is_fallback=True)

    contamination = min(0.1, max(0.01, 1.0 / x.shape[0]))
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(x)
    return ExpenseAnomalyDetector(model=model, category_to_id=category_to_id, is_fallback=False)
