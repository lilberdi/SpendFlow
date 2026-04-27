from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    description: str = Field(min_length=1)
    amount: float = Field(ge=0)
    category: str = Field(min_length=1)
    tags: list[str] = []
    source: Literal['manual', 'ocr'] = 'manual'
    ocr_merchant_raw: str | None = None
    ocr_raw_text: str | None = None
    ocr_confidence: float | None = Field(default=None, ge=0, le=1)
    receipt_storage_key: str | None = None


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
    source: str = 'manual'
    ocr_merchant_raw: str | None = None
    ocr_raw_text: str | None = None
    ocr_confidence: float | None = None
    receipt_storage_key: str | None = None

    model_config = {'from_attributes': True}


class ReceiptOcrResponse(BaseModel):
    amount: float = Field(..., ge=0)
    category: str
    merchant: str | None = None
    confidence: float = Field(..., ge=0, le=1)
    mock: bool = True
    dataset_note: str = (
        'Заглушка OCR в стиле SROIE (TOTAL / DATE / текст). Подключите Tesseract+layout при продакшене.'
    )
    raw_text_stub: str = ''


class TransactionPage(BaseModel):
    items: list[TransactionRead]
    total: int
