from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from sklearn.ensemble import IsolationForest


@dataclass
class ExpenseAnomalyDetector:
    model: IsolationForest
    category_to_id: dict[str, int]

    def score(self, amount: float, category: str) -> tuple[str, float]:
        if amount <= 0:
            return 'invalid', -1.0
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


def _train_detector() -> ExpenseAnomalyDetector:
    rng = np.random.default_rng(42)
    categories = {
        'Transport': (500, 1500),
        'Food': (1500, 4000),
        'Shopping': (3000, 8000),
        'Entertainment': (1000, 3000),
        'Coffee': (800, 2000),
        'Other': (500, 3000),
    }
    rows: list[list[float]] = []
    category_to_id: dict[str, int] = {}
    for idx, (cat, (low, high)) in enumerate(categories.items()):
        category_to_id[cat] = idx
        for amount in rng.uniform(low, high, size=200):
            rows.append([float(amount), float(idx)])
    x = np.array(rows)

    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(x)
    return ExpenseAnomalyDetector(model=model, category_to_id=category_to_id)


@lru_cache(maxsize=1)
def get_expense_anomaly_detector() -> ExpenseAnomalyDetector:
    return _train_detector()
