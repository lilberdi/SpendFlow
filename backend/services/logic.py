import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
RULES_PATH = BASE_DIR / 'data' / 'raw' / 'rules.json'


def load_rules() -> dict[str, Any]:
    with RULES_PATH.open('r', encoding='utf-8') as fp:
        return json.load(fp)


def check_rules(data: dict[str, Any]) -> str:
    rules = load_rules()

    if rules['critical_rules']['block_if_budget_exceeded'] and data.get('is_budget_exceeded', False):
        return '⛔️ Критическая ошибка: Общий бюджет уже превышен. Новая трата заблокирована.'

    if data['amount'] < rules['thresholds']['min_amount']:
        return '⛔️ Критическая ошибка: Сумма траты не может быть отрицательной'

    for tag in data.get('tags_list', []):
        if tag in rules['lists']['blacklist']:
            return f'⛔️ Критическая ошибка: Найден запрещенный тег ({tag})'

    if rules['critical_rules']['must_not_exceed_total_budget']:
        current_total = data.get('total_spent', 0) + data['amount']
        if current_total > rules['thresholds']['max_total_budget']:
            return (
                f"❌ Отказ: Превышен общий лимит бюджета ({rules['thresholds']['max_total_budget']}). "
                f'Текущая сумма: {current_total}'
            )

    if rules['critical_rules']['must_not_exceed_category_budget']:
        category = data.get('category', 'Other')
        category_limits = rules['thresholds']['max_category_budget']
        if category in category_limits:
            new_category_total = data.get('category_total', 0) + data['amount']
            category_limit = category_limits[category]
            if new_category_total > category_limit:
                return (
                    f"❌ Отказ: Превышен лимит категории '{category}' ({category_limit}). "
                    f"Текущая сумма по категории: {data.get('category_total', 0)}, "
                    f"новая трата: {data['amount']}, итого: {new_category_total}"
                )
            if new_category_total >= category_limit * 0.8:
                return (
                    f"⚠️ Предупреждение: Приближение к лимиту категории '{category}'. "
                    f'Использовано {new_category_total} из {category_limit} '
                    f"({int(new_category_total / category_limit * 100)}%)"
                )

    has_whitelist_tag = any(tag in rules['lists']['whitelist'] for tag in data.get('tags_list', []))
    success_msg = '✅ Успех: Трата соответствует правилам контроля бюджета'
    if has_whitelist_tag:
        success_msg += ' (найден подтвержденный тег)'
    return success_msg
