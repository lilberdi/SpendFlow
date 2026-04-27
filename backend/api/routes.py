from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db_session
from backend.repositories.transactions import TransactionRepository
from backend.repositories.budgets import BudgetRepository
from backend.schemas.analytics import (
    AnomaliesResponse,
    AnomalyScoreRequest,
    AnomalyScoreResponse,
    BudgetProbabilityResponse,
    ForecastResponse,
    RecommendationRequest,
    RulesCheckRequest,
    TransactionAnomaly,
)
from backend.schemas.budget import BudgetCreate, BudgetRead
from backend.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate
from backend.services.anomaly import build_expense_anomaly_detector
from backend.services.forecast import budget_success_probability, forecast_next_month
from backend.services.logic import check_rules
from backend.services.recommendations import get_smart_recommendations
from backend.services.rules import check_monthly_category_limit

router = APIRouter(prefix='/api/v1', tags=['api'])
logger = logging.getLogger(__name__)


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    # Accept both trailing Z and explicit timezone offset formats.
    normalized = value.strip().replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f'Invalid datetime format: {value}') from exc


@router.get('/health')
async def health() -> dict[str, str]:
    return {'status': 'ok'}


@router.post('/transactions', response_model=TransactionRead)
async def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db_session)) -> TransactionRead:
    limit_result = check_monthly_category_limit(
        db=db,
        category_name=payload.category.strip(),
        transaction_amount=float(payload.amount),
    )
    repo = TransactionRepository(db)
    created = repo.create(payload)
    return TransactionRead(
        id=created.id,
        created_at=created.created_at,
        description=created.description,
        amount=created.amount,
        category=created.category,
        tags=created.tags,
        limit_warning=limit_result.limit_warning,
        warning_message=limit_result.message,
    )


@router.get('/transactions', response_model=list[TransactionRead])
async def list_transactions(
    limit: int = 200,
    category: str | None = None,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    amount_min: float | None = None,
    amount_max: float | None = None,
    db: Session = Depends(get_db_session),
) -> list[TransactionRead]:
    repo = TransactionRepository(db)
    return repo.list(
        limit=limit,
        category=category,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
    )


@router.get('/transactions/sum')
async def sum_transactions(
    request: Request,
    category: str | None = None,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    amount_min: float | None = None,
    amount_max: float | None = None,
    limit: int | None = None,
    db: Session = Depends(get_db_session),
) -> dict[str, float]:
    repo = TransactionRepository(db)
    date_from_dt = _parse_iso_datetime(date_from)
    date_to_dt = _parse_iso_datetime(date_to)
    logger.info(
        'sum_transactions params raw=%s parsed=%s',
        dict(request.query_params),
        {
            'category': category,
            'date_from': date_from_dt.isoformat() if date_from_dt else None,
            'date_to': date_to_dt.isoformat() if date_to_dt else None,
            'amount_min': amount_min,
            'amount_max': amount_max,
            'limit': limit,
        },
    )
    return {
        'total': repo.sum(
            category=category,
            date_from=date_from_dt,
            date_to=date_to_dt,
            amount_min=amount_min,
            amount_max=amount_max,
        )
    }


@router.get('/budgets', response_model=list[BudgetRead])
async def list_budgets(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    db: Session = Depends(get_db_session),
) -> list[BudgetRead]:
    repo = BudgetRepository(db)
    rows = repo.list(month=month, year=year)
    result: list[BudgetRead] = []
    for row in rows:
        spent = repo.spent_for_period(category_name=row.category_name, month=row.month, year=row.year)
        ratio = spent / row.limit_amount if row.limit_amount > 0 else 0.0
        result.append(
            BudgetRead(
                id=row.id,
                category_name=row.category_name,
                limit_amount=float(row.limit_amount),
                month=row.month,
                year=row.year,
                spent_amount=spent,
                usage_ratio=ratio,
            )
        )
    return result


@router.post('/budgets', response_model=BudgetRead)
async def upsert_budget(payload: BudgetCreate, db: Session = Depends(get_db_session)) -> BudgetRead:
    repo = BudgetRepository(db)
    row = repo.upsert(payload)
    spent = repo.spent_for_period(category_name=row.category_name, month=row.month, year=row.year)
    ratio = spent / row.limit_amount if row.limit_amount > 0 else 0.0
    return BudgetRead(
        id=row.id,
        category_name=row.category_name,
        limit_amount=float(row.limit_amount),
        month=row.month,
        year=row.year,
        spent_amount=spent,
        usage_ratio=ratio,
    )


@router.get('/transactions/{transaction_id}', response_model=TransactionRead)
async def get_transaction(transaction_id: int, db: Session = Depends(get_db_session)) -> TransactionRead:
    repo = TransactionRepository(db)
    row = repo.get(transaction_id)
    if row is None:
        raise HTTPException(status_code=404, detail='Transaction not found')
    return row


@router.put('/transactions/{transaction_id}', response_model=TransactionRead)
async def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db_session),
) -> TransactionRead:
    repo = TransactionRepository(db)
    row = repo.update(transaction_id, payload)
    if row is None:
        raise HTTPException(status_code=404, detail='Transaction not found')
    return row


@router.delete('/transactions/{transaction_id}')
async def delete_transaction(transaction_id: int, db: Session = Depends(get_db_session)) -> dict[str, bool]:
    repo = TransactionRepository(db)
    return {'deleted': repo.delete(transaction_id)}


@router.post('/rules/check')
async def rules_check(payload: RulesCheckRequest, db: Session = Depends(get_db_session)) -> dict[str, str]:
    repo = TransactionRepository(db)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    data = payload.model_dump()
    if data.get('total_spent') is None:
        data['total_spent'] = repo.sum(date_from=month_start)
    if data.get('category_total') is None:
        data['category_total'] = repo.sum(category=payload.category, date_from=month_start)
    if data.get('is_budget_exceeded') is None:
        # Для rule-check считаем признаком превышения общий лимит из rules.json внутри check_rules.
        data['is_budget_exceeded'] = False
    return {'result': check_rules(data)}


@router.get('/forecast', response_model=ForecastResponse)
async def forecast(total_limit: float = Query(..., gt=0), db: Session = Depends(get_db_session)) -> ForecastResponse:
    value, chart_data = forecast_next_month(total_limit=total_limit, db=db)
    return ForecastResponse(forecast=value, chart_data=chart_data)


@router.get('/forecast/probability', response_model=BudgetProbabilityResponse)
async def forecast_probability(
    total_spent: float = Query(..., ge=0),
    total_limit: float = Query(..., gt=0),
    day_of_month: int | None = Query(default=None, ge=1, le=31),
    days_in_month: int = Query(default=30, ge=28, le=31),
) -> BudgetProbabilityResponse:
    prob, explanation = budget_success_probability(
        total_spent=total_spent,
        total_limit=total_limit,
        day_of_month=day_of_month,
        days_in_month=days_in_month,
    )
    return BudgetProbabilityResponse(probability=prob, explanation=explanation)


@router.post('/anomalies/score', response_model=AnomalyScoreResponse)
async def anomaly_score(payload: AnomalyScoreRequest, db: Session = Depends(get_db_session)) -> AnomalyScoreResponse:
    detector = build_expense_anomaly_detector(db)
    label, score = detector.score(amount=payload.amount, category=payload.category)
    return AnomalyScoreResponse(label=label, score=score)


@router.get('/anomalies', response_model=AnomaliesResponse)
async def anomalies(limit: int = Query(default=200, ge=1, le=500), db: Session = Depends(get_db_session)) -> AnomaliesResponse:
    repo = TransactionRepository(db)
    transactions = repo.list(limit=limit)
    detector = build_expense_anomaly_detector(db)

    items = []
    for tx in transactions:
        label, score = detector.score(amount=float(tx.amount), category=tx.category)
        items.append(
            TransactionAnomaly(
                id=int(tx.id),
                category=tx.category,
                amount=float(tx.amount),
                anomaly_label=label,
                anomaly_score=float(score),
                is_anomaly=label == 'anomaly',
            )
        )

    source = 'postgres+isolation_forest' if not detector.is_fallback else 'postgres_insufficient_history'
    return AnomaliesResponse(source=source, transactions=items)


@router.post('/recommendations')
async def recommendations(payload: RecommendationRequest) -> dict[str, list[str]]:
    tips = get_smart_recommendations(**payload.model_dump())
    return {'recommendations': tips}
