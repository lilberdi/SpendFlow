from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Tuple

import numpy as np
from sklearn.ensemble import IsolationForest


@dataclass
class ExpenseAnomalyDetector:
    """
    Модель для обнаружения «нетипичных» трат.
    Использует IsolationForest по признакам (amount, category_id).
    """

    model: IsolationForest
    category_to_id: Dict[str, int]

    def score(self, amount: float, category: str) -> Tuple[str, float]:
        """
        Возвращает (уровень_аномалии, score).

        score ~ 1  → всё нормально
        score ~ 0  → подозрительно
        score < 0  → сильно выбивается
        """
        if amount <= 0:
            return "invalid", -1.0

        cat_id = self.category_to_id.get(category, -1)
        x = np.array([[amount, float(cat_id)]])
        raw_score = float(self.model.decision_function(x)[0])

        if raw_score > 0.1:
            label = "normal"
        elif raw_score > -0.2:
            label = "warning"
        else:
            label = "anomaly"

        return label, raw_score


def _generate_synthetic_data() -> Tuple[np.ndarray, Dict[str, int]]:
    """
    Генерирует имитационные данные трат по категориям.
    Диапазоны подобраны вручную для учебных целей.
    """
    rng = np.random.default_rng(42)

    categories = {
        "Transport": (500, 1500),
        "Food": (1500, 4000),
        "Shopping": (3000, 8000),
        "Entertainment": (1000, 3000),
        "Coffee": (800, 2000),
        "Other": (500, 3000),
    }

    features = []
    category_to_id: Dict[str, int] = {}

    for idx, (cat, (low, high)) in enumerate(categories.items()):
        category_to_id[cat] = idx
        # 200 случайных трат в диапазоне [low, high]
        amounts = rng.uniform(low, high, size=200)
        for a in amounts:
            features.append([a, float(idx)])

    X = np.array(features)
    return X, category_to_id


def _train_anomaly_detector() -> ExpenseAnomalyDetector:
    X, cat_map = _generate_synthetic_data()
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(X)
    return ExpenseAnomalyDetector(model=model, category_to_id=cat_map)


@lru_cache(maxsize=1)
def get_expense_anomaly_detector() -> ExpenseAnomalyDetector:
    """
    Возвращает обученный детектор аномалий.
    Обучение выполняется один раз и кэшируется.
    """
    return _train_anomaly_detector()

