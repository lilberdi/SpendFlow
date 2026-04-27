"""
Заглушка OCR в духе SROIE (receipt: TOTAL, DATE, блоки текста).
Реальный пайплайн: layout → NER → нормализация суммы; здесь — детерминированный mock по имени файла и размеру.
"""

from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class MockOcrResult:
    amount: float
    category: str
    merchant: str | None
    confidence: float
    raw_text_stub: str


# Набор «как из датасета чеков»: TOTAL + категория + продавец
_SROIE_STYLE_PRESETS: list[MockOcrResult] = [
    MockOcrResult(
        12450.0,
        'Food',
        "McDonald's",
        0.88,
        'DATE 12/05/2024\nTOTAL 12450.00\nADDRESS Almaty',
    ),
    MockOcrResult(
        3890.0,
        'Transport',
        'Yandex Taxi',
        0.91,
        'DATE 12/05/2024\nTOTAL 3890.00\nSERVICE ride',
    ),
    MockOcrResult(
        15600.0,
        'Shopping',
        'Magnum',
        0.86,
        'DATE 11/28/2024\nTOTAL 15600.00\nTHANK YOU',
    ),
    MockOcrResult(
        9200.0,
        'Bills',
        'Kcell',
        0.84,
        'DATE 12/01/2024\nTOTAL 9200.00\nMOBILE BILL',
    ),
    MockOcrResult(
        6700.0,
        'Leisure',
        'Ticketon',
        0.82,
        'DATE 12/03/2024\nTOTAL 6700.00\nEVENT TICKET',
    ),
]


def mock_sroie_receipt_ocr(filename: str, file_size: int) -> MockOcrResult:
    seed = hashlib.sha256(f'{filename}:{file_size}'.encode()).digest()
    idx = seed[0] % len(_SROIE_STYLE_PRESETS)
    base = _SROIE_STYLE_PRESETS[idx]
    jitter = (seed[1] % 200) - 100
    amount = max(100.0, base.amount + float(jitter))
    conf = min(0.97, max(0.75, base.confidence + (seed[2] % 20) / 1000))
    return MockOcrResult(
        amount=round(amount, 2),
        category=base.category,
        merchant=base.merchant,
        confidence=round(conf, 3),
        raw_text_stub=base.raw_text_stub + f'\nFILE {filename}\nBYTES {file_size}',
    )
