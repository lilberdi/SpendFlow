from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    category_name: str = Field(min_length=1)
    limit_amount: float = Field(gt=0)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)


class BudgetRead(BaseModel):
    id: int
    category_name: str
    limit_amount: float
    month: int
    year: int
    spent_amount: float = 0.0
    usage_ratio: float = 0.0

    model_config = {'from_attributes': True}
