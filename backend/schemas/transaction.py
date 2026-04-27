from datetime import datetime

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    description: str = Field(min_length=1)
    amount: float = Field(ge=0)
    category: str = Field(min_length=1)
    tags: list[str] = []


class TransactionUpdate(BaseModel):
    description: str | None = None
    amount: float | None = Field(default=None, ge=0)
    category: str | None = None
    tags: list[str] | None = None


class TransactionRead(BaseModel):
    id: int
    created_at: datetime
    description: str
    amount: float
    category: str
    tags: str
    limit_warning: bool = False
    warning_message: str | None = None

    model_config = {'from_attributes': True}
