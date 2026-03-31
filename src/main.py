import streamlit as st
from datetime import date
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Для работы без GUI

from mock_data import test_entity as default_data
from logic import check_rules, load_rules, process_text_message
from knowledge_graph import create_graph, find_related_entities, get_category_for_store, get_stores_in_category
from ml_classifier import get_default_classifier
from anomaly_detector import get_expense_anomaly_detector
from forecast import forecast_next_month, budget_success_probability
from report_generator import generate_weekly_report, generate_monthly_summary
from expense_clustering import get_expense_clusters
from recommendations import get_smart_recommendations
from database import init_db, add_transaction, fetch_recent_transactions, sum_amounts_since
import networkx as nx


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

# ---------------------------------------------------------------------------
# Локальная база SQLite: создаём файл и таблицу при каждом запуске скрипта.
# Это дёшево по времени (CREATE IF NOT EXISTS) и гарантирует готовность хранилища
# до любых кнопок «Сохранить».
# ---------------------------------------------------------------------------
init_db()

# Инициализация графа знаний (создается один раз и кэшируется)
@st.cache_resource
def get_knowledge_graph():
    """Создает и возвращает граф знаний для классификации транзакций."""
    return create_graph()

kg = get_knowledge_graph()


# Инициализация ML‑классификатора категорий расходов
@st.cache_resource
def get_expense_classifier():
    return get_default_classifier()


expense_classifier = get_expense_classifier()


# Инициализация детектора аномалий расходов
@st.cache_resource
def get_anomaly_detector():
    return get_expense_anomaly_detector()


anomaly_detector = get_anomaly_detector()

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

# ── Прогноз расходов и вероятность бюджета ──
forecast_val, chart_data = forecast_next_month(total_limit)
prob, prob_explanation = budget_success_probability(
    total_spent=current_total,
    total_limit=total_limit,
)

forecast_col1, forecast_col2 = st.columns([1.5, 1])
with forecast_col1:
    st.markdown(
        '<div class="spendflow-section-title">Прогноз расходов на следующий месяц</div>',
        unsafe_allow_html=True,
    )
    fig_fc, ax_fc = plt.subplots(figsize=(8, 4))
    ax_fc.bar(chart_data["months"][:-1], chart_data["actual"], color="#3B82F6", alpha=0.7, label="Факт")
    ax_fc.bar(chart_data["months"][-1], chart_data["forecast"], color="#F97316", alpha=0.7, label="Прогноз")
    ax_fc.axhline(y=total_limit, color="red", linestyle="--", linewidth=2, label=f"Лимит {total_limit:,.0f} ₸")
    ax_fc.legend()
    ax_fc.set_ylabel("₸")
    plt.tight_layout()
    st.pyplot(fig_fc, use_container_width=True)

with forecast_col2:
    st.markdown(
        '<div class="spendflow-section-title">Вероятность уложиться в бюджет</div>',
        unsafe_allow_html=True,
    )
    st.metric(
        label="Оценка",
        value=f"{prob:.0f}%",
        delta=prob_explanation[:60] + "..." if len(prob_explanation) > 60 else prob_explanation,
    )
    st.caption(prob_explanation)

st.write("")

# ── Умные рекомендации ──
category_totals_demo = {
    user_category: new_category_total,
    **{c: 0 for c in category_limits if c != user_category},
}
tips = get_smart_recommendations(
    current_total=current_total,
    total_limit=total_limit,
    category_totals=category_totals_demo,
    category_limits=category_limits,
    current_transaction_amount=user_amount,
    current_category=user_category,
)
st.markdown('<div class="spendflow-section-title">Умные рекомендации</div>', unsafe_allow_html=True)
for tip in tips:
    st.write(f"• {tip}")

st.write("")

# ── Текстовый отчёт ──
weekly_amounts = [12000, 8000, 9500, 11000, 15000, 13000, 7000]
weekly_report = generate_weekly_report(weekly_amounts)
category_totals_report = {
    user_category: new_category_total,
    **{c: 0 for c in category_limits if c != user_category},
}
monthly_report = generate_monthly_summary(
    category_totals=category_totals_report,
    total_spent=current_total,
    total_limit=total_limit,
)
st.markdown('<div class="spendflow-section-title">Итоги недели и месяца</div>', unsafe_allow_html=True)
st.markdown(weekly_report)
st.markdown(monthly_report)

st.write("")

# ── Кластеризация трат (K-Means) ──
clusters = get_expense_clusters(n_clusters=4)
st.markdown('<div class="spendflow-section-title">Типы трат (кластеризация K-Means)</div>', unsafe_allow_html=True)
cluster_cols = st.columns(4)
for i, cluster in enumerate(clusters):
    with cluster_cols[i % 4]:
        st.markdown(f"**{cluster['name']}**")
        st.caption(cluster["description"])

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

    # Предсказание категории с помощью ML‑классификатора
    ml_category, ml_prob = expense_classifier.predict(current_test_data["description"])
    st.write(f"**ML‑категория (по описанию):** {ml_category} ({ml_prob * 100:.0f}%)")

    # Оценка «нетипичности» траты (анализ аномалий)
    anomaly_label, anomaly_score = anomaly_detector.score(
        amount=current_test_data["amount"],
        category=current_test_data["category"],
    )
    if anomaly_label == "normal":
        st.write(f"**Аномалия:** нормальная трата (score={anomaly_score:.2f})")
    elif anomaly_label == "warning":
        st.write(f"**Аномалия:** на границе нормы (score={anomaly_score:.2f})")
    else:
        st.write(f"**Аномалия:** ⚠ нетипично высокая трата (score={anomaly_score:.2f})")

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

st.write("")

# ── История трат в SQLite (персистентное хранилище) ──
# Здесь пользователь может зафиксировать текущую форму как запись в файле
# spendflow.db в корне проекта. Данные переживают перезапуск Streamlit.
# Это не замена полноценному банковскому импорту, но — первый шаг к «реальной» истории.
st.markdown(
    '<div class="spendflow-section-title">История трат (SQLite)</div>',
    unsafe_allow_html=True,
)

hist_col1, hist_col2 = st.columns([1, 1.2])

with hist_col1:
    st.caption(
        "Файл базы: `spendflow.db` в корне репозитория (в `.gitignore`, не коммитится). "
        "Сохраняется описание, сумма, категория и теги из текущей формы слева."
    )
    if st.button("💾 Сохранить текущую трату в историю", key="save_tx_sqlite"):
        try:
            new_id = add_transaction(
                description=user_description,
                amount=float(user_amount),
                category=user_category,
                tags=current_test_data["tags_list"],
            )
            st.success(f"Запись добавлена (id={new_id}). Обновите страницу или прокрутите таблицу ниже.")
        except Exception as e:
            st.error(f"Не удалось сохранить: {e}")

    total_in_db = sum_amounts_since()
    st.metric("Сумма всех сохранённых трат в БД", f"{total_in_db:,.0f} ₸".replace(",", " "))

with hist_col2:
    recent = fetch_recent_transactions(limit=30)
    if recent:
        df_hist = pd.DataFrame(recent)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.info("Пока нет сохранённых записей. Заполните форму слева и нажмите «Сохранить».")

st.write("")

# ── Граф знаний ──
st.markdown('<div class="spendflow-section-title">Граф знаний: Магазины и Категории</div>', unsafe_allow_html=True)

graph_col1, graph_col2 = st.columns([1.5, 1])

with graph_col1:
    # Визуализация графа с помощью matplotlib
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Получаем позиции узлов для красивого отображения
    pos = {}
    
    # Разделяем узлы по типам
    stores = []
    categories = []
    for node in kg.nodes():
        node_type = kg.nodes[node].get("type", "unknown")
        if node_type == "store":
            stores.append(node)
        elif node_type == "category":
            categories.append(node)
    
    # Располагаем категории слева, магазины справа
    import numpy as np
    n_categories = len(categories)
    n_stores = len(stores)
    
    # Категории слева
    for i, cat in enumerate(categories):
        pos[cat] = (0, i * 1.5)
    
    # Магазины справа
    for i, store in enumerate(stores):
        pos[store] = (3, i * 0.8)
    
    # Рисуем связи
    for edge in kg.edges():
        ax.plot([pos[edge[0]][0], pos[edge[1]][0]], 
                [pos[edge[0]][1], pos[edge[1]][1]], 
                'gray', alpha=0.3, linewidth=1.5)
    
    # Рисуем узлы-категории (кружки, синие)
    for cat in categories:
        ax.scatter(pos[cat][0], pos[cat][1], s=2000, c='#3B82F6', alpha=0.7, edgecolors='darkblue', linewidths=2)
        ax.text(pos[cat][0], pos[cat][1], cat, ha='center', va='center', 
                fontsize=10, fontweight='bold', color='white')
    
    # Рисуем узлы-магазины (кружки, оранжевые)
    for store in stores:
        ax.scatter(pos[store][0], pos[store][1], s=1500, c='#F97316', alpha=0.7, 
                  edgecolors='darkorange', linewidths=2)
        ax.text(pos[store][0], pos[store][1], store, ha='center', va='center', 
                fontsize=9, fontweight='bold', color='white')
    
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(-1, max(len(categories) * 1.5, len(stores) * 0.8) + 1)
    ax.axis('off')
    ax.set_title('Граф знаний: Связи между магазинами и категориями', 
                 fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)

with graph_col2:
    st.markdown("**Информация о графе:**")
    
    # Получаем узлы по типам
    stores = [node for node in kg.nodes() if kg.nodes[node].get("type") == "store"]
    categories = [node for node in kg.nodes() if kg.nodes[node].get("type") == "category"]
    
    st.write(f"**Узлы:**")
    st.write(f"- Магазинов: {len(stores)}")
    st.write(f"- Категорий: {len(categories)}")
    
    edges = list(kg.edges())
    st.write(f"**Связей:** {len(edges)}")
    
    st.write("**Магазины:**")
    for store in sorted(stores):
        category = get_category_for_store(kg, store)
        st.write(f"- {store} → {category}")
    
    st.write("**Категории:**")
    for cat in sorted(categories):
        stores_in_cat = get_stores_in_category(kg, cat)
        st.write(f"- {cat} ({len(stores_in_cat)} магазинов)")
    
    # Демонстрация автоматической классификации
    st.markdown("**🔍 Автоклассификация:**")
    test_store = st.text_input("Введите название магазина:", value="Uber", key="test_store")
    if test_store:
        predicted_category = get_category_for_store(kg, test_store)
        if predicted_category != "Other":
            st.success(f"'{test_store}' → категория '{predicted_category}'")
        else:
            st.warning(f"Магазин '{test_store}' не найден в графе знаний")
    
    # Демонстрация функции find_related_entities
    st.markdown("**🔗 Поиск связанных объектов:**")
    test_node = st.text_input("Введите узел для поиска связей:", value="Transport", key="test_node")
    if test_node:
        related = find_related_entities(kg, test_node)
        if related:
            st.info(f"Связанные с '{test_node}': {', '.join(related)}")
        else:
            st.warning(f"Узел '{test_node}' не найден или не имеет связей")

st.write("")

# ── Knowledge Graph Explorer ──
st.markdown('<div class="spendflow-section-title">Knowledge Graph Explorer 🕸</div>', unsafe_allow_html=True)

explorer_col1, explorer_col2 = st.columns([1, 1.5])

with explorer_col1:
    st.write("**Выбор узла для анализа:**")
    
    # Получаем все узлы графа
    all_nodes = list(kg.nodes())
    selected_node = st.selectbox(
        "Выберите объект для поиска связей:",
        all_nodes,
        key="explorer_node"
    )
    
    # Показываем информацию о выбранном узле
    node_type = kg.nodes[selected_node].get("type", "unknown")
    st.write(f"**Тип:** {node_type}")
    
    # Кнопка поиска
    if st.button("🔍 Найти связи", type="primary", use_container_width=True, key="find_relations"):
        results = find_related_entities(kg, selected_node)
        if results:
            st.success(f"Объект '{selected_node}' связан с:")
            for result in results:
                result_type = kg.nodes[result].get("type", "unknown")
                st.write(f"- **{result}** ({result_type})")
        else:
            st.info(f"Объект '{selected_node}' не имеет связей")

with explorer_col2:
    st.write("**Визуализация структуры графа:**")
    
    # Создаем визуализацию с помощью spring_layout
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Раскладка (layout) - как расположить точки
    pos = nx.spring_layout(kg, k=1.5, iterations=50)
    
    # Разделяем узлы по типам для разных цветов
    stores = [node for node in kg.nodes() if kg.nodes[node].get("type") == "store"]
    categories = [node for node in kg.nodes() if kg.nodes[node].get("type") == "category"]
    
    # Рисуем связи
    nx.draw_networkx_edges(kg, pos, edge_color='gray', alpha=0.3, width=1.5, ax=ax)
    
    # Рисуем узлы-категории (синие)
    if categories:
        nx.draw_networkx_nodes(kg, pos, nodelist=categories, 
                              node_color='#3B82F6', node_size=2000, 
                              alpha=0.7, ax=ax)
    
    # Рисуем узлы-магазины (оранжевые)
    if stores:
        nx.draw_networkx_nodes(kg, pos, nodelist=stores, 
                              node_color='#F97316', node_size=1500, 
                              alpha=0.7, ax=ax)
    
    # Выделяем выбранный узел (красный)
    if selected_node in kg:
        nx.draw_networkx_nodes(kg, pos, nodelist=[selected_node], 
                              node_color='red', node_size=2500, 
                              alpha=0.9, ax=ax)
    
    # Подписи узлов
    nx.draw_networkx_labels(kg, pos, font_size=9, font_weight='bold', ax=ax)
    
    ax.set_title('Граф знаний: Структура связей', fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)

st.write("")

# ── Chatbot: SpendFlow Assistant ──
st.markdown('<div class="spendflow-section-title">SpendFlow Chatbot</div>', unsafe_allow_html=True)

# 1. Инициализация истории чата (память)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Отрисовка истории диалога
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. Поле ввода (сообщение пользователя)
user_prompt = st.chat_input("Введите ваш запрос про расходы, магазины или категории...")

if user_prompt:
    # 3.1. Сохраняем сообщение пользователя
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 3.2. Получаем ответ от «мозга» (граф знаний + умные рекомендации по бюджету)
    chat_context = {
        "current_total": current_total,
        "total_limit": total_limit,
        "category_totals": {
            user_category: new_category_total,
            **{c: 0 for c in category_limits if c != user_category},
        },
        "category_limits": category_limits,
        "amount": user_amount,
        "category": user_category,
    }
    bot_reply = process_text_message(user_prompt, kg, context=chat_context)

    # 3.3. Сохраняем ответ бота
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    with st.chat_message("assistant"):
        st.markdown(bot_reply)

st.write("")

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
        
        **Граф знаний:**
        - Автоматически определяет категорию по названию магазина
        - Связывает магазины с категориями расходов
        - Используется для классификации новых транзакций
        """
    )

