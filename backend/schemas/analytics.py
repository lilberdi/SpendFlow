from pydantic import BaseModel, Field


class RulesCheckRequest(BaseModel):
    description: str
    amount: float
    category: str
    category_total: float = 0
    total_spent: float = 0
    is_budget_exceeded: bool = False
    tags_list: list[str] = []


class ForecastResponse(BaseModel):
    forecast: float
    chart_data: dict


class BudgetProbabilityResponse(BaseModel):
    probability: float
    explanation: str


class AnomalyScoreRequest(BaseModel):
    amount: float = Field(gt=0)
    category: str


class AnomalyScoreResponse(BaseModel):
    label: str
    score: float


class RecommendationRequest(BaseModel):
    current_total: float
    total_limit: float
    category_totals: dict[str, float]
    category_limits: dict[str, float]
    current_transaction_amount: float = 0
    current_category: str | None = None
