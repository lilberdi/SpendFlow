import json
import os

# Автоматическое определение пути к файлу
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_PATH = os.path.join(BASE_DIR, 'data', 'raw', 'rules.json')


def load_rules():
    """Загружает правила из JSON файла."""
    with open(RULES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_rules(data):
    """
    Принимает словарь данных транзакции (data), возвращает строковый вердикт.
    
    Args:
        data: словарь с полями:
            - description: описание траты
            - amount: сумма траты
            - category: категория траты
            - tags_list: список тегов
            - is_budget_exceeded: флаг превышения общего бюджета
            - category_total: текущая сумма трат по категории
    
    Returns:
        str: вердикт о соответствии правилам
    """
    rules = load_rules()
    
    # --- 1. HARD FILTERS (Критические проверки) ---
    
    # Проверка: если общий бюджет уже превышен, блокируем новую трату
    if rules['critical_rules']['block_if_budget_exceeded'] and data.get('is_budget_exceeded', False):
        return "⛔️ Критическая ошибка: Общий бюджет уже превышен. Новая трата заблокирована."
    
    # Проверка: сумма траты должна быть положительной
    if data['amount'] < rules['thresholds']['min_amount']:
        return "⛔️ Критическая ошибка: Сумма траты не может быть отрицательной"
    
    # Проверка на запрещенные элементы в тегах (Blacklist)
    for tag in data.get('tags_list', []):
        if tag in rules['lists']['blacklist']:
            return f"⛔️ Критическая ошибка: Найден запрещенный тег ({tag})"
    
    # --- 2. БИЗНЕС-ЛОГИКА (Сравнение с лимитами) ---
    
    # Проверка превышения общего бюджета
    if rules['critical_rules']['must_not_exceed_total_budget']:
        # Предполагаем, что data содержит текущую сумму всех трат
        current_total = data.get('total_spent', 0) + data['amount']
        if current_total > rules['thresholds']['max_total_budget']:
            return f"❌ Отказ: Превышен общий лимит бюджета ({rules['thresholds']['max_total_budget']}). Текущая сумма: {current_total}"
    
    # Проверка превышения лимита по категории
    if rules['critical_rules']['must_not_exceed_category_budget']:
        category = data.get('category', 'Other')
        category_limits = rules['thresholds']['max_category_budget']
        
        if category in category_limits:
            # Проверяем, не превысит ли новая трата лимит категории
            new_category_total = data.get('category_total', 0) + data['amount']
            category_limit = category_limits[category]
            
            if new_category_total > category_limit:
                return f"❌ Отказ: Превышен лимит категории '{category}' ({category_limit}). " \
                       f"Текущая сумма по категории: {data.get('category_total', 0)}, " \
                       f"новая трата: {data['amount']}, итого: {new_category_total}"
            
            # Предупреждение при приближении к лимиту (80% от лимита)
            if new_category_total >= category_limit * 0.8:
                return f"⚠️ Предупреждение: Приближение к лимиту категории '{category}'. " \
                       f"Использовано {new_category_total} из {category_limit} ({int(new_category_total/category_limit*100)}%)"
    
    # Проверка на наличие элементов из whitelist (опционально)
    has_whitelist_tag = any(tag in rules['lists']['whitelist'] for tag in data.get('tags_list', []))
    
    # Если все проверки пройдены
    success_msg = f"✅ Успех: Трата соответствует правилам контроля бюджета"
    if has_whitelist_tag:
        success_msg += " (найден подтвержденный тег)"
    
    return success_msg

