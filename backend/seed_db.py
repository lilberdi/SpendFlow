from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import random

from sqlalchemy import text

from backend.db.models import BudgetModel, TransactionModel
from backend.db.session import SessionLocal


@dataclass(frozen=True)
class MonthBucket:
    year: int
    month: int
    target_total: float


CATEGORIES = ["Transport", "Food", "Leisure", "Shopping", "Bills"]
TARGETS = [50000.0, 55000.0, 52000.0, 58000.0, 60000.0, 62000.0]
DESCRIPTIONS = {
    "Transport": ["Uber ride", "Taxi to office", "Fuel top-up", "Metro card refill"],
    "Food": ["Lunch", "Groceries", "Coffee", "Dinner delivery"],
    "Leisure": ["Cinema tickets", "Weekend trip", "Game subscription", "Concert"],
    "Shopping": ["Clothes", "Electronics accessory", "Marketplace order", "Household goods"],
    "Bills": ["Electricity bill", "Internet bill", "Mobile plan", "Water utility"],
}


def _first_day_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _last_full_months(now: datetime, count: int = 6) -> list[MonthBucket]:
    first_current = _first_day_of_month(now)
    month_cursor = first_current - timedelta(days=1)
    months: list[tuple[int, int]] = []
    for _ in range(count):
        months.append((month_cursor.year, month_cursor.month))
        month_cursor = _first_day_of_month(month_cursor) - timedelta(days=1)
    months.reverse()
    return [MonthBucket(year=y, month=m, target_total=t) for (y, m), t in zip(months, TARGETS, strict=True)]


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    this_month = datetime(year, month, 1, tzinfo=timezone.utc)
    return (next_month - this_month).days


def _generate_month_transactions(bucket: MonthBucket, rng: random.Random) -> list[TransactionModel]:
    tx_count = rng.randint(16, 22)
    category_weights = [0.22, 0.30, 0.14, 0.20, 0.14]
    rows: list[TransactionModel] = []
    raw_amounts: list[float] = []

    for _ in range(tx_count):
        category = rng.choices(CATEGORIES, weights=category_weights, k=1)[0]
        if category == "Transport":
            amount = rng.uniform(900, 4500)
        elif category == "Food":
            amount = rng.uniform(1200, 6000)
        elif category == "Leisure":
            amount = rng.uniform(1500, 9000)
        elif category == "Shopping":
            amount = rng.uniform(2500, 12000)
        else:
            amount = rng.uniform(2000, 10000)
        raw_amounts.append(amount)
        day = rng.randint(1, _days_in_month(bucket.year, bucket.month))
        created_at = datetime(bucket.year, bucket.month, day, rng.randint(8, 22), rng.randint(0, 59), tzinfo=timezone.utc)
        rows.append(
            TransactionModel(
                created_at=created_at,
                description=rng.choice(DESCRIPTIONS[category]),
                amount=amount,
                category=category,
                tags="seed,demo",
            )
        )

    factor = bucket.target_total / max(sum(raw_amounts), 1.0)
    for row in rows:
        row.amount = round(max(300.0, row.amount * factor), 2)
    return rows


def _generate_current_month_anomalies(now: datetime) -> list[TransactionModel]:
    year = now.year
    month = now.month
    base_day = min(now.day, 20)
    anomalies = [
        ("Shopping", 210000.0, "Premium laptop purchase"),
        ("Leisure", 185000.0, "Luxury weekend trip"),
        ("Transport", 160000.0, "Emergency car repair"),
    ]
    rows: list[TransactionModel] = []
    for idx, (category, amount, description) in enumerate(anomalies):
        rows.append(
            TransactionModel(
                created_at=datetime(year, month, max(1, base_day - idx), 14, 30, tzinfo=timezone.utc),
                description=description,
                amount=amount,
                category=category,
                tags="seed,anomaly",
            )
        )
    return rows


def _seed_budgets(months: list[MonthBucket], now: datetime) -> list[BudgetModel]:
    # Лимиты для полного месяца (часть категорий будут превышены) + для текущего месяца.
    last_full = months[-1]
    budget_rows = [
        BudgetModel(category_name="Food", limit_amount=14000, month=last_full.month, year=last_full.year),
        BudgetModel(category_name="Shopping", limit_amount=11000, month=last_full.month, year=last_full.year),
        BudgetModel(category_name="Transport", limit_amount=9000, month=last_full.month, year=last_full.year),
        BudgetModel(category_name="Bills", limit_amount=12000, month=last_full.month, year=last_full.year),
        BudgetModel(category_name="Leisure", limit_amount=10000, month=last_full.month, year=last_full.year),
        BudgetModel(category_name="Shopping", limit_amount=80000, month=now.month, year=now.year),
        BudgetModel(category_name="Leisure", limit_amount=70000, month=now.month, year=now.year),
        BudgetModel(category_name="Transport", limit_amount=60000, month=now.month, year=now.year),
    ]
    return budget_rows


def seed() -> None:
    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    months = _last_full_months(now, count=6)

    session = SessionLocal()
    try:
        session.execute(text("TRUNCATE TABLE transactions, budgets RESTART IDENTITY CASCADE;"))

        rows: list[TransactionModel] = []
        for bucket in months:
            rows.extend(_generate_month_transactions(bucket, rng))
        rows.extend(_generate_current_month_anomalies(now))
        session.add_all(rows)

        budget_rows = _seed_budgets(months, now)
        session.add_all(budget_rows)

        session.commit()

        print("Seed completed successfully.")
        print(f"Inserted transactions: {len(rows)}")
        print(f"Inserted budgets: {len(budget_rows)}")
        print("Run command: python3 -m backend.seed_db")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
