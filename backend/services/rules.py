from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.repositories.budgets import BudgetRepository


@dataclass
class LimitCheckResult:
    limit_warning: bool
    message: str | None
    current_spent: float
    projected_spent: float
    limit_amount: float | None


def check_monthly_category_limit(
    db: Session,
    category_name: str,
    transaction_amount: float,
    at_time: datetime | None = None,
) -> LimitCheckResult:
    now = at_time or datetime.now(timezone.utc)
    month = now.month
    year = now.year

    repo = BudgetRepository(db)
    budget = repo.get_for_period(category_name=category_name, month=month, year=year)
    current_spent = repo.spent_for_period(category_name=category_name, month=month, year=year)
    projected_spent = current_spent + float(transaction_amount)

    if budget is None:
        return LimitCheckResult(
            limit_warning=False,
            message=None,
            current_spent=current_spent,
            projected_spent=projected_spent,
            limit_amount=None,
        )

    if projected_spent > budget.limit_amount:
        over = projected_spent - budget.limit_amount
        return LimitCheckResult(
            limit_warning=True,
            message=(
                f"Превышение лимита категории '{category_name}' за {month:02d}.{year}: "
                f"лимит {budget.limit_amount:,.0f} ₸, прогноз {projected_spent:,.0f} ₸, "
                f"перерасход {over:,.0f} ₸."
            ),
            current_spent=current_spent,
            projected_spent=projected_spent,
            limit_amount=float(budget.limit_amount),
        )

    return LimitCheckResult(
        limit_warning=False,
        message=None,
        current_spent=current_spent,
        projected_spent=projected_spent,
        limit_amount=float(budget.limit_amount),
    )
