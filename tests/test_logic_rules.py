# -*- coding: utf-8 -*-
"""Unit-тесты ключевых правил бюджета: load_rules, check_rules."""

import logic


def test_load_rules_returns_expected_top_level_keys():
    rules = logic.load_rules()
    assert "thresholds" in rules
    assert "lists" in rules
    assert "critical_rules" in rules
    assert "max_total_budget" in rules["thresholds"]
    assert "max_category_budget" in rules["thresholds"]


def test_check_rules_success_under_limits(monkeypatch, sample_rules):
    monkeypatch.setattr(logic, "load_rules", lambda: sample_rules)
    data = {
        "description": "кофе",
        "amount": 100,
        "category": "Food",
        "tags_list": [],
        "is_budget_exceeded": False,
        "category_total": 0,
        "total_spent": 0,
    }
    out = logic.check_rules(data)
    assert "✅ Успех" in out


def test_check_rules_whitelist_appends_note(monkeypatch, sample_rules):
    monkeypatch.setattr(logic, "load_rules", lambda: sample_rules)
    data = {
        "description": "x",
        "amount": 50,
        "category": "Other",
        "tags_list": ["verified"],
        "is_budget_exceeded": False,
        "category_total": 0,
        "total_spent": 0,
    }
    out = logic.check_rules(data)
    assert "подтвержденный тег" in out


def test_check_rules_blocks_when_budget_already_exceeded(monkeypatch, sample_rules):
    monkeypatch.setattr(logic, "load_rules", lambda: sample_rules)
    data = {
        "description": "x",
        "amount": 1,
        "category": "Other",
        "tags_list": [],
        "is_budget_exceeded": True,
        "category_total": 0,
        "total_spent": 0,
    }
    out = logic.check_rules(data)
    assert "⛔️" in out
    assert "превышен" in out.lower()


def test_check_rules_negative_amount(monkeypatch, sample_rules):
    monkeypatch.setattr(logic, "load_rules", lambda: sample_rules)
    data = {
        "description": "x",
        "amount": -10,
        "category": "Other",
        "tags_list": [],
        "is_budget_exceeded": False,
        "category_total": 0,
        "total_spent": 0,
    }
    out = logic.check_rules(data)
    assert "⛔️" in out
    assert "отрицательн" in out.lower()


def test_check_rules_blacklist_tag(monkeypatch, sample_rules):
    monkeypatch.setattr(logic, "load_rules", lambda: sample_rules)
    data = {
        "description": "x",
        "amount": 10,
        "category": "Other",
        "tags_list": ["fraud"],
        "is_budget_exceeded": False,
        "category_total": 0,
        "total_spent": 0,
    }
    out = logic.check_rules(data)
    assert "⛔️" in out
    assert "fraud" in out


def test_check_rules_total_budget_exceeded(monkeypatch, sample_rules):
    monkeypatch.setattr(logic, "load_rules", lambda: sample_rules)
    data = {
        "description": "x",
        "amount": 500,
        "category": "Other",
        "tags_list": [],
        "is_budget_exceeded": False,
        "category_total": 0,
        "total_spent": 9_600,
    }
    out = logic.check_rules(data)
    assert "❌" in out
    assert "общий" in out.lower()


def test_check_rules_category_hard_limit(monkeypatch, sample_rules):
    monkeypatch.setattr(logic, "load_rules", lambda: sample_rules)
    data = {
        "description": "ужин",
        "amount": 300,
        "category": "Food",
        "tags_list": [],
        "is_budget_exceeded": False,
        "category_total": 800,
        "total_spent": 0,
    }
    out = logic.check_rules(data)
    assert "❌" in out
    assert "Food" in out


def test_check_rules_category_warning_near_limit(monkeypatch, sample_rules):
    monkeypatch.setattr(logic, "load_rules", lambda: sample_rules)
    data = {
        "description": "обед",
        "amount": 50,
        "category": "Food",
        "tags_list": [],
        "is_budget_exceeded": False,
        "category_total": 850,
        "total_spent": 0,
    }
    out = logic.check_rules(data)
    assert "⚠️" in out
    assert "Приближение" in out


def test_check_rules_unknown_category_skips_category_limit(monkeypatch, sample_rules):
    """Категория не из max_category_budget — ветка лимита по категории не срабатывает."""
    monkeypatch.setattr(logic, "load_rules", lambda: sample_rules)
    data = {
        "description": "x",
        "amount": 100,
        "category": "NonExistingCategory",
        "tags_list": [],
        "is_budget_exceeded": False,
        "category_total": 0,
        "total_spent": 0,
    }
    out = logic.check_rules(data)
    assert "✅ Успех" in out


def test_check_rules_critical_flags_can_disable_total_check(monkeypatch, sample_rules):
    """При выключенном контроле общего бюджета большая сумма допустима (категория без лимита в правилах)."""
    sample_rules["critical_rules"]["must_not_exceed_total_budget"] = False
    monkeypatch.setattr(logic, "load_rules", lambda: sample_rules)
    data = {
        "description": "x",
        "amount": 50_000,
        "category": "NoBudgetCategory",
        "tags_list": [],
        "is_budget_exceeded": False,
        "category_total": 0,
        "total_spent": 9_000,
    }
    out = logic.check_rules(data)
    assert "✅ Успех" in out
