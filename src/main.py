import streamlit as st
from datetime import date
import pandas as pd

from mock_data import test_entity as default_data
from logic import check_rules, load_rules


st.set_page_config(
    page_title="SpendFlow Dashboard",
    page_icon="💸",
    layout="wide",
)

# Немного кастомного оформления под дашборд
st.markdown(
    """
    <style>
        body {
            background-color: #F3F4F6;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        .spendflow-title {
            font-size: 1.9rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }
        .spendflow-subtitle {
            color: #6B7280;
            font-size: 0.95rem;
        }
        .spendflow-section-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 1.2rem;
            margin-bottom: 0.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

rules = load_rules()

# ───── ЛЕВАЯ ПАНЕЛЬ (Навигация + фильтры) ─────
with st.sidebar:
    st.markdown("### 💸 SpendFlow")
    st.caption("Учёт расходов и контроль бюджета")

    st.markdown("---")
    st.markdown("**Навигация**")
    st.write("• Overview (текущий экран)")
    st.write("• Rules debugger")
    st.write("• Settings")

    st.markdown("---")
    st.markdown("**Фильтр по периоду**")
    _start, _end = st.date_input(
        "Период анализа",
        value=(date.today().replace(day=1), date.today()),
    )

    st.markdown("---")
    st.markdown("**Параметры транзакции**")

    user_description = st.text_input(
        "Описание траты",
        value=default_data["description"],
    )

    user_amount = st.number_input(
        "Сумма траты (₸)",
        min_value=0,
        value=default_data["amount"],
        step=100,
    )

    categories = ["Transport", "Food", "Shopping", "Entertainment", "Other"]
    user_category = st.selectbox(
        "Категория",
        options=categories,
        index=categories.index(default_data["category"])
        if default_data["category"] in categories
        else 0,
    )

    user_category_total = st.number_input(
        "Текущая сумма по категории (₸)",
        min_value=0,
        value=default_data["category_total"],
        step=100,
    )

    user_total_spent = st.number_input(
        "Общая сумма всех трат (₸)",
        min_value=0,
        value=default_data.get("total_spent", 0),
        step=100,
    )

    st.markdown("**Критические флаги**")
    user_budget_exceeded = st.checkbox(
        "Бюджет уже превышен",
        value=default_data["is_budget_exceeded"],
    )

    tags_input = st.text_input(
        "Теги (через запятую)",
        value=", ".join(default_data["tags_list"]),
    )


# ───── ОСНОВНОЙ ДАШБОРД ─────
st.markdown(
    f"""
    <div class="spendflow-title">Dashboard</div>
    <div class="spendflow-subtitle">
        Контроль бюджета и анализ расходов · {date.today().strftime("%d.%m.%Y")}
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")  # небольшой отступ

# Собираем объект данных
current_test_data = {
    "description": user_description,
    "amount": user_amount,
    "category": user_category,
    "category_total": user_category_total,
    "total_spent": user_total_spent,
    "is_budget_exceeded": user_budget_exceeded,
    "tags_list": [tag.strip() for tag in tags_input.split(",") if tag.strip()],
}

total_limit = rules["thresholds"]["max_total_budget"]
category_limits = rules["thresholds"]["max_category_budget"]
category_limit = category_limits.get(user_category, category_limits.get("Other", total_limit))

current_total = current_test_data["total_spent"] + current_test_data["amount"]
new_category_total = current_test_data["category_total"] + current_test_data["amount"]

remaining_total = max(total_limit - current_total, 0)
remaining_category = max(category_limit - new_category_total, 0)

usage_total_pct = min(int(current_total / total_limit * 100), 999) if total_limit else 0
usage_cat_pct = min(int(new_category_total / category_limit * 100), 999) if category_limit else 0

# ── Верхний ряд карточек (метрики) ──
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="spendflow-section-title">Total money spent</div>', unsafe_allow_html=True)
    st.metric(
        label="Всего потрачено (включая текущую операцию)",
        value=f"{current_total:,.0f} ₸".replace(",", " "),
        delta=f"Осталось {remaining_total:,.0f} ₸ до лимита".replace(",", " "),
    )

with col2:
    st.markdown('<div class="spendflow-section-title">Category status</div>', unsafe_allow_html=True)
    st.metric(
        label=f"{user_category} · использовано {usage_cat_pct}%",
        value=f"{new_category_total:,.0f} ₸".replace(",", " "),
        delta=f"Лимит {category_limit:,.0f} ₸".replace(",", " "),
    )

with col3:
    st.markdown('<div class="spendflow-section-title">Budget health</div>', unsafe_allow_html=True)
    status_text = "OK"
    if user_budget_exceeded or current_total > total_limit or new_category_total > category_limit:
        status_text = "⚠ Риск перерасхода"
    elif usage_total_pct >= 80 or usage_cat_pct >= 80:
        status_text = "На грани лимитов"

    st.metric(
        label="Статус бюджета",
        value=status_text,
        delta=f"Общий лимит {total_limit:,.0f} ₸".replace(",", " "),
    )

st.write("")  # отступ

# ── Блок графиков, как на современном дашборде ──
chart_col1, chart_col2 = st.columns((2, 1.2))

with chart_col1:
    st.markdown(
        '<div class="spendflow-section-title">Динамика трат за неделю</div>',
        unsafe_allow_html=True,
    )
    weekly_data = pd.DataFrame(
        {
            "День": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
            "Расходы, ₸": [12000, 8000, 9500, 11000, 15000, 13000, 7000],
        }
    ).set_index("День")
    st.bar_chart(weekly_data, height=260)

with chart_col2:
    st.markdown(
        '<div class="spendflow-section-title">Категория: факт vs лимит</div>',
        unsafe_allow_html=True,
    )
    cat_chart = pd.DataFrame(
        {
            "Тип": ["Факт", "Остаток лимита"],
            "Сумма, ₸": [
                new_category_total,
                max(category_limit - new_category_total, 0),
            ],
        }
    ).set_index("Тип")
    st.area_chart(cat_chart, height=260)

st.write("")

# ── Детали транзакции и результат проверки ──
st.markdown('<div class="spendflow-section-title">Текущая транзакция</div>', unsafe_allow_html=True)

details_col, result_col = st.columns([1.2, 1.0])

with details_col:
    st.write(f"**Описание:** {current_test_data['description']}")
    st.write(f"**Категория:** {current_test_data['category']}")
    st.write(f"**Сумма:** {current_test_data['amount']} ₸")
    st.write(f"**Сумма по категории (до операции):** {current_test_data['category_total']} ₸")
    st.write(f"**Общая сумма трат (до операции):** {current_test_data['total_spent']} ₸")
    st.write(
        f"**Теги:** {', '.join(current_test_data['tags_list']) if current_test_data['tags_list'] else 'нет'}"
    )

with result_col:
    st.write("**Проверка правил**")
    run_check = st.button("🔍 Запустить проверку", type="primary", use_container_width=True)

    if run_check:
        result = check_rules(current_test_data)

        if "✅" in result:
            st.success(result)
        elif "⛔️" in result:
            st.error(result)
        elif "❌" in result:
            st.error(result)
        elif "⚠️" in result:
            st.warning(result)
        else:
            st.info(result)
    else:
        st.info("Нажмите кнопку, чтобы выполнить проверку по правилам.")


with st.expander("ℹ️ Правила и лимиты"):
    st.write(
        """
        **Правила контроля бюджета (из `rules.json`):**

        1. **Критические проверки (Hard Filters):**
           - Бюджет не должен быть уже превышен.
           - Сумма траты должна быть неотрицательной.
           - Запрещены теги из blacklist (`fraud`, `suspicious`).

        2. **Проверка лимитов:**
           - Общий бюджет: 10 000 ₸.
           - Лимиты по категориям:
             - Transport: 5 000 ₸
             - Food: 3 000 ₸
             - Shopping: 2 000 ₸
             - Entertainment: 1 500 ₸
             - Other: 1 000 ₸

        3. **Предупреждения:**
           - При достижении ~80% лимита категории показывается предупреждение.
        """
    )

