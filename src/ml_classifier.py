from dataclasses import dataclass
from functools import lru_cache
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


@dataclass
class TrainingSample:
    text: str
    category: str


def _build_training_data() -> List[TrainingSample]:
    """
    Простые имитационные данные для классификации расходов по описанию.
    Темы подобраны под наш проект SpendFlow.
    """
    samples = [
        # Transport
        TrainingSample("uber ride home", "Transport"),
        TrainingSample("yandex taxi to work", "Transport"),
        TrainingSample("bolt taxi airport", "Transport"),
        TrainingSample("metro ticket", "Transport"),
        TrainingSample("bus card top up", "Transport"),
        # Food
        TrainingSample("mcdonalds burger and coke", "Food"),
        TrainingSample("kfc chicken bucket", "Food"),
        TrainingSample("lunch in restaurant", "Food"),
        TrainingSample("grocery store food", "Food"),
        TrainingSample("dinner in cafe", "Food"),
        # Coffee
        TrainingSample("starbucks latte", "Coffee"),
        TrainingSample("starbucks cappuccino", "Coffee"),
        TrainingSample("coffee to go", "Coffee"),
        TrainingSample("americano with milk", "Coffee"),
        # Shopping
        TrainingSample("magnum supermarket shopping", "Shopping"),
        TrainingSample("clothes in mall", "Shopping"),
        TrainingSample("electronics purchase", "Shopping"),
        TrainingSample("buy shoes in store", "Shopping"),
        # Entertainment
        TrainingSample("cinema tickets", "Entertainment"),
        TrainingSample("netflix subscription", "Entertainment"),
        TrainingSample("concert ticket", "Entertainment"),
        TrainingSample("game subscription", "Entertainment"),
        # Other
        TrainingSample("mobile phone bill", "Other"),
        TrainingSample("internet bill", "Other"),
        TrainingSample("unknown expense", "Other"),
    ]
    return samples


@dataclass
class ExpenseCategoryClassifier:
    """
    Простой ML‑классификатор категории расходов по тексту описания.
    Использует TF‑IDF + Logistic Regression.
    """

    pipeline: Pipeline
    classes_: List[str]

    def predict(self, text: str) -> Tuple[str, float]:
        """
        Возвращает (предсказанная_категория, вероятность).
        """
        if not text:
            return "Other", 0.0

        probs = self.pipeline.predict_proba([text])[0]
        best_idx = int(np.argmax(probs))
        return self.classes_[best_idx], float(probs[best_idx])


def _train_classifier() -> ExpenseCategoryClassifier:
    samples = _build_training_data()
    texts = [s.text for s in samples]
    labels = [s.category for s in samples]

    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )

    pipeline.fit(texts, labels)
    classes = list(pipeline.classes_)
    return ExpenseCategoryClassifier(pipeline=pipeline, classes_=classes)


@lru_cache(maxsize=1)
def get_default_classifier() -> ExpenseCategoryClassifier:
    """
    Возвращает обученный классификатор.
    Обучение выполняется один раз и кэшируется.
    """
    return _train_classifier()

