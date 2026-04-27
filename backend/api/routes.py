from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.session import get_db_session
from backend.repositories.transactions import TransactionRepository
from backend.repositories.budgets import BudgetRepository
from backend.repositories.regular_payments import RegularPaymentRepository
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
from backend.schemas.budget import BudgetBatchUpsert, BudgetCreate, BudgetRead
from backend.schemas.dashboard import DashboardResponse
from backend.schemas.payment import RegularPaymentCreate, UpcomingPaymentRead
from backend.schemas.transaction import ReceiptOcrResponse, TransactionCreate, TransactionPage, TransactionRead, TransactionUpdate
from backend.services.anomaly import build_expense_anomaly_detector
from backend.services.forecast import budget_success_probability, forecast_next_month
from backend.services.logic import check_rules
from backend.services.recommendations import get_smart_recommendations
from backend.services.rules import check_monthly_category_limit
from backend.services.ocr_mock import mock_sroie_receipt_ocr
from backend.services.regular_payment_logic import advance_next_charge, compute_pay_now_amount
from backend.db.models import BudgetModel, TransactionModel

router = APIRouter(prefix='/api/v1', tags=['api'])
logger = logging.getLogger(__name__)


def _transaction_read(
    row: TransactionModel,
    limit_warning: bool = False,
    warning_message: str | None = None,
) -> TransactionRead:
    return TransactionRead(
        id=int(row.id),
        created_at=row.created_at,
        description=row.description,
        amount=float(row.amount),
        category=row.category,
        tags=row.tags,
        limit_warning=limit_warning,
        warning_message=warning_message,
        source=getattr(row, 'source', None) or 'manual',
        ocr_merchant_raw=row.ocr_merchant_raw,
        ocr_raw_text=row.ocr_raw_text,
        ocr_confidence=row.ocr_confidence,
        receipt_storage_key=row.receipt_storage_key,
    )


def _budget_read(repo: BudgetRepository, row: BudgetModel) -> BudgetRead:
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


@router.get('/dashboard', response_model=DashboardResponse)
async def dashboard(db: Session = Depends(get_db_session)) -> DashboardResponse:
    """Aggregated dashboard payload for the React SPA (month scope in UTC)."""
    total_limit = float(settings.spendflow_total_limit)
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    tx_repo = TransactionRepository(db)
    budget_repo = BudgetRepository(db)

    month_total = tx_repo.sum(date_from=month_start, date_to=now)

    forecast_value, chart_data = forecast_next_month(total_limit=total_limit, db=db)
    months = chart_data.get('months', [])
    actual = chart_data.get('actual', [])
    forecast_last = float(chart_data.get('forecast', 0.0))
    chart_expense_amounts: list[float] = []
    for idx, _m in enumerate(months):
        if idx < len(actual):
            chart_expense_amounts.append(float(actual[idx]))
        else:
            chart_expense_amounts.append(forecast_last)
    raw_flags = chart_data.get('expense_is_forecast')
    if isinstance(raw_flags, list) and len(raw_flags) == len(months):
        chart_expense_forecast_flags = [bool(x) for x in raw_flags]
    elif months:
        chart_expense_forecast_flags = [False] * (len(months) - 1) + [True]
    else:
        chart_expense_forecast_flags = []

    remaining = total_limit - month_total

    month_rows = tx_repo.list(limit=200, date_from=month_start, date_to=now)
    detector = build_expense_anomaly_detector(db)
    anomaly_ids: list[int] = []
    for row in month_rows:
        label, _score = detector.score(amount=float(row.amount), category=row.category)
        if label == 'anomaly':
            anomaly_ids.append(int(row.id))
    anomalies_this_month = len(anomaly_ids)

    budget_rows = budget_repo.list(month=now.month, year=now.year)
    budgets = [_budget_read(budget_repo, row) for row in budget_rows]

    recent = [_transaction_read(r) for r in month_rows[:20]]

    return DashboardResponse(
        month_total=month_total,
        forecast=forecast_value,
        total_limit=total_limit,
        remaining=remaining,
        anomalies_this_month=anomalies_this_month,
        chart_months=months,
        chart_expense_amounts=chart_expense_amounts,
        chart_expense_forecast_flags=chart_expense_forecast_flags,
        forecast_note=chart_data.get('message'),
        budgets=budgets,
        recent_transactions=recent,
        anomaly_ids=anomaly_ids,
    )


@router.post('/transactions', response_model=TransactionRead)
async def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db_session)) -> TransactionRead:
    limit_result = check_monthly_category_limit(
        db=db,
        category_name=payload.category.strip(),
        transaction_amount=float(payload.amount),
    )
    repo = TransactionRepository(db)
    created = repo.create(payload)
    return _transaction_read(
        created,
        limit_warning=limit_result.limit_warning,
        warning_message=limit_result.message,
    )


@router.post('/transactions/upload-receipt', response_model=ReceiptOcrResponse)
async def upload_receipt_mock(file: UploadFile = File(...)) -> ReceiptOcrResponse:
    """Mock OCR (SROIE-style): возвращает amount и category без сохранения файла."""
    raw = await file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='Файл слишком большой (макс. 5 МБ)')
    name = file.filename or 'receipt.jpg'
    mock = mock_sroie_receipt_ocr(name, len(raw))
    return ReceiptOcrResponse(
        amount=mock.amount,
        category=mock.category,
        merchant=mock.merchant,
        confidence=mock.confidence,
        raw_text_stub=mock.raw_text_stub,
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
    rows = repo.list(
        limit=limit,
        category=category,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
    )
    return [_transaction_read(r) for r in rows]


def _first_of_next_month_utc(now: datetime) -> datetime:
    if now.month == 12:
        return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


@router.get('/transactions/paged', response_model=TransactionPage)
async def list_transactions_paged(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, description='Поиск по названию или категории'),
    category: str | None = None,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    amount_min: float | None = None,
    amount_max: float | None = None,
    db: Session = Depends(get_db_session),
) -> TransactionPage:
    repo = TransactionRepository(db)
    total = repo.count(
        category=category,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        search=q,
    )
    rows = repo.list(
        limit=limit,
        offset=skip,
        category=category,
        date_from=date_from,
        date_to=date_to,
        amount_min=amount_min,
        amount_max=amount_max,
        search=q,
    )
    items = [_transaction_read(r) for r in rows]
    return TransactionPage(items=items, total=total)


_PERIODICITY_ALLOWED = frozenset({'monthly', 'weekly', 'yearly'})


@router.get('/payments/upcoming', response_model=list[UpcomingPaymentRead])
async def payments_upcoming(db: Session = Depends(get_db_session)) -> list[UpcomingPaymentRead]:
    """Регулярные платежи: сумма «к оплате» из БД, лимит/факт по категории, риск перерасхода."""
    reg_repo = RegularPaymentRepository(db)
    budget_repo = BudgetRepository(db)
    now = datetime.now(timezone.utc)
    rows = reg_repo.list_all()
    pay_nows: dict[int, float] = {
        int(r.id): compute_pay_now_amount(
            amount=float(r.amount),
            periodicity=r.periodicity,
            last_paid_at=r.last_paid_at,
            now=now,
        )
        for r in rows
    }
    due_by_category: dict[str, float] = {}
    for r in rows:
        pn = pay_nows[int(r.id)]
        if pn > 0:
            c = r.category_name
            due_by_category[c] = due_by_category.get(c, 0.0) + pn

    out: list[UpcomingPaymentRead] = []
    for r in rows:
        budget = budget_repo.get_for_period(category_name=r.category_name, month=now.month, year=now.year)
        planned = float(budget.limit_amount) if budget else 0.0
        spent = budget_repo.spent_for_period(category_name=r.category_name, month=now.month, year=now.year)
        remainder = planned - spent
        due_total = due_by_category.get(r.category_name, 0.0)
        overspend = budget is not None and due_total > remainder + 1e-6

        out.append(
            UpcomingPaymentRead(
                regular_payment_id=int(r.id),
                name=r.name,
                category_name=r.category_name,
                periodicity=r.periodicity,
                planned_amount=planned,
                spent_amount=spent,
                pay_now_amount=pay_nows[int(r.id)],
                next_charge_at=r.next_charge_at,
                overspend_risk=overspend,
            )
        )
    return out


@router.post('/payments/regular', response_model=UpcomingPaymentRead)
async def create_regular_payment(payload: RegularPaymentCreate, db: Session = Depends(get_db_session)) -> UpcomingPaymentRead:
    per = payload.periodicity.strip().lower()
    if per not in _PERIODICITY_ALLOWED:
        raise HTTPException(status_code=422, detail='periodicity должен быть: monthly, weekly или yearly')
    now = datetime.now(timezone.utc)
    next_at = payload.next_charge_at or _first_of_next_month_utc(now)
    reg_repo = RegularPaymentRepository(db)
    row = reg_repo.create(
        RegularPaymentCreate(
            name=payload.name,
            amount=payload.amount,
            category_name=payload.category_name,
            periodicity=per,
            next_charge_at=next_at,
        )
    )
    budget_repo = BudgetRepository(db)
    budget = budget_repo.get_for_period(category_name=row.category_name, month=now.month, year=now.year)
    planned = float(budget.limit_amount) if budget else 0.0
    spent = budget_repo.spent_for_period(category_name=row.category_name, month=now.month, year=now.year)
    pay_now = compute_pay_now_amount(
        amount=float(row.amount), periodicity=row.periodicity, last_paid_at=row.last_paid_at, now=now
    )
    all_rows = reg_repo.list_all()
    due_by_category: dict[str, float] = {}
    for s in all_rows:
        pn = compute_pay_now_amount(
            amount=float(s.amount), periodicity=s.periodicity, last_paid_at=s.last_paid_at, now=now
        )
        if pn > 0:
            due_by_category[s.category_name] = due_by_category.get(s.category_name, 0.0) + pn
    remainder = planned - spent
    due_total = due_by_category.get(row.category_name, 0.0)
    overspend = budget is not None and due_total > remainder + 1e-6
    return UpcomingPaymentRead(
        regular_payment_id=int(row.id),
        name=row.name,
        category_name=row.category_name,
        periodicity=row.periodicity,
        planned_amount=planned,
        spent_amount=spent,
        pay_now_amount=pay_now,
        next_charge_at=row.next_charge_at,
        overspend_risk=overspend,
    )


@router.post('/payments/regular/{payment_id}/pay', response_model=TransactionRead)
async def pay_regular_payment(payment_id: int, db: Session = Depends(get_db_session)) -> TransactionRead:
    reg_repo = RegularPaymentRepository(db)
    sub = reg_repo.get(payment_id)
    if sub is None:
        raise HTTPException(status_code=404, detail='Регулярный платёж не найден')
    now = datetime.now(timezone.utc)
    pay_now = compute_pay_now_amount(
        amount=float(sub.amount),
        periodicity=sub.periodicity,
        last_paid_at=sub.last_paid_at,
        now=now,
    )
    if pay_now <= 0:
        raise HTTPException(
            status_code=400,
            detail='Сейчас нет суммы к оплате: период уже закрыт оплатой или сумма нулевая.',
        )
    limit_result = check_monthly_category_limit(
        db=db,
        category_name=sub.category_name.strip(),
        transaction_amount=pay_now,
    )
    tx_repo = TransactionRepository(db)
    payload = TransactionCreate(
        description=f'Регулярный платёж: {sub.name}',
        amount=pay_now,
        category=sub.category_name.strip(),
        tags=['regular_payment', f'regular_payment:{sub.id}'],
    )
    created = tx_repo.create(payload)
    sub.last_paid_at = now
    sub.next_charge_at = advance_next_charge(sub.next_charge_at, sub.periodicity)
    reg_repo.save(sub)
    return _transaction_read(
        created,
        limit_warning=limit_result.limit_warning,
        warning_message=limit_result.message,
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
    return [_budget_read(repo, r) for r in rows]


@router.post('/budgets', response_model=BudgetRead)
async def upsert_budget(payload: BudgetCreate, db: Session = Depends(get_db_session)) -> BudgetRead:
    repo = BudgetRepository(db)
    row = repo.upsert(payload)
    return _budget_read(repo, row)


@router.post('/budgets/batch', response_model=list[BudgetRead])
async def upsert_budgets_batch(payload: BudgetBatchUpsert, db: Session = Depends(get_db_session)) -> list[BudgetRead]:
    repo = BudgetRepository(db)
    rows = repo.upsert_batch(payload.items)
    return [_budget_read(repo, r) for r in rows]


@router.get('/transactions/{transaction_id}', response_model=TransactionRead)
async def get_transaction(transaction_id: int, db: Session = Depends(get_db_session)) -> TransactionRead:
    repo = TransactionRepository(db)
    row = repo.get(transaction_id)
    if row is None:
        raise HTTPException(status_code=404, detail='Transaction not found')
    return _transaction_read(row)


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
    return _transaction_read(row)


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
