from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db_session
from backend.repositories.transactions import TransactionRepository
from backend.schemas.analytics import (
    AnomalyScoreRequest,
    AnomalyScoreResponse,
    BudgetProbabilityResponse,
    ForecastResponse,
    RecommendationRequest,
    RulesCheckRequest,
)
from backend.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate
from backend.services.anomaly import get_expense_anomaly_detector
from backend.services.forecast import budget_success_probability, forecast_next_month
from backend.services.logic import check_rules
from backend.services.recommendations import get_smart_recommendations

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
    repo = TransactionRepository(db)
    return repo.create(payload)


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
async def rules_check(payload: RulesCheckRequest) -> dict[str, str]:
    return {'result': check_rules(payload.model_dump())}


@router.get('/forecast', response_model=ForecastResponse)
async def forecast(total_limit: float = Query(..., gt=0)) -> ForecastResponse:
    value, chart_data = forecast_next_month(total_limit=total_limit)
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
async def anomaly_score(payload: AnomalyScoreRequest) -> AnomalyScoreResponse:
    detector = get_expense_anomaly_detector()
    label, score = detector.score(amount=payload.amount, category=payload.category)
    return AnomalyScoreResponse(label=label, score=score)


@router.post('/recommendations')
async def recommendations(payload: RecommendationRequest) -> dict[str, list[str]]:
    tips = get_smart_recommendations(**payload.model_dump())
    return {'recommendations': tips}
