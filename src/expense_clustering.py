# src/expense_clustering.py
"""
Кластеризация трат (K-Means) для выявления типов расходов.
"""
from functools import lru_cache
from typing import Dict, List, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# Кодировка категорий
CATEGORY_ENCODING = {
    "Transport": 0,
    "Food": 1,
    "Shopping": 2,
    "Entertainment": 3,
    "Coffee": 4,
    "Other": 5,
}


def _build_synthetic_transactions() -> np.ndarray:
    """
    Синтетические траты для кластеризации.
    Признаки: [amount, category_encoded, is_weekend].
    """
    np.random.seed(123)
    samples = []
    
    # Транспорт: 300–800
    for _ in range(30):
        samples.append([np.random.uniform(300, 800), CATEGORY_ENCODING["Transport"], 0])
    
    # Еда: 500–3000
    for _ in range(40):
        samples.append([np.random.uniform(500, 3000), CATEGORY_ENCODING["Food"], np.random.choice([0, 1])])
    
    # Крупные покупки: 5000–30000
    for _ in range(20):
        samples.append([np.random.uniform(5000, 30000), CATEGORY_ENCODING["Shopping"], 0])
    
    # Развлечения: 500–2500
    for _ in range(25):
        samples.append([np.random.uniform(500, 2500), CATEGORY_ENCODING["Entertainment"], 1])
    
    # Кофе: 300–800
    for _ in range(35):
        samples.append([np.random.uniform(300, 800), CATEGORY_ENCODING["Coffee"], 0])
    
    # Прочее: разброс
    for _ in range(20):
        samples.append([np.random.uniform(100, 2000), CATEGORY_ENCODING["Other"], np.random.choice([0, 1])])
    
    return np.array(samples)


def get_expense_clusters(n_clusters: int = 4) -> List[Dict]:
    """
    Кластеризация трат K-Means.
    
    Returns:
        Список кластеров с описанием: название, средняя сумма, доля, описание.
    """
    X = _build_synthetic_transactions()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    
    cluster_names = [
        "Повседневные траты",
        "Крупные покупки",
        "Развлечения и отдых",
        "Транспорт и кофе",
    ][:n_clusters]
    
    results = []
    for i in range(n_clusters):
        mask = labels == i
        amounts = X[mask, 0]
        avg = float(np.mean(amounts))
        count = int(np.sum(mask))
        pct = count / len(X) * 100
        
        name = cluster_names[i] if i < len(cluster_names) else f"Кластер {i+1}"
        desc = f"Средняя сумма: {avg:,.0f} ₸. Доля трат: {pct:.0f}%."
        
        results.append({
            "name": name,
            "avg_amount": avg,
            "count": count,
            "pct": pct,
            "description": desc,
        })
    
    return results
