"""Идемпотентные правки схемы для существующих БД (create_all не добавляет колонки)."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_transaction_ocr_columns(engine: Engine) -> None:
    insp = inspect(engine)
    cols = {c['name'] for c in insp.get_columns('transactions')}
    with engine.begin() as conn:
        if 'source' not in cols:
            conn.execute(
                text(
                    "ALTER TABLE transactions ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'manual'"
                )
            )
        if 'ocr_merchant_raw' not in cols:
            conn.execute(text("ALTER TABLE transactions ADD COLUMN ocr_merchant_raw VARCHAR(512)"))
        if 'ocr_raw_text' not in cols:
            conn.execute(text("ALTER TABLE transactions ADD COLUMN ocr_raw_text TEXT"))
        if 'ocr_confidence' not in cols:
            conn.execute(text("ALTER TABLE transactions ADD COLUMN ocr_confidence DOUBLE PRECISION"))
        if 'receipt_storage_key' not in cols:
            conn.execute(text("ALTER TABLE transactions ADD COLUMN receipt_storage_key VARCHAR(512)"))
