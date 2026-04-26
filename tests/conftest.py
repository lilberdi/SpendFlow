# -*- coding: utf-8 -*-
"""Общие фикстуры для тестов SpendFlow."""

import copy
from typing import Any, Dict

import pytest

# Минимальная копия структуры rules.json для изолированных unit-тестов check_rules.
SAMPLE_RULES: Dict[str, Any] = {
    "thresholds": {
        "min_amount": 0,
        "max_total_budget": 10_000,
        "max_category_budget": {
            "Food": 1_000,
            "Transport": 2_000,
            "Other": 500,
        },
    },
    "lists": {
        "whitelist": ["verified", "confirmed"],
        "blacklist": ["fraud", "suspicious"],
    },
    "critical_rules": {
        "must_not_exceed_total_budget": True,
        "must_not_exceed_category_budget": True,
        "block_if_budget_exceeded": True,
    },
}


@pytest.fixture
def sample_rules() -> Dict[str, Any]:
    return copy.deepcopy(SAMPLE_RULES)
