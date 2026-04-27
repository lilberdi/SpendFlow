from datetime import date, datetime, time, timezone
import os

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

matplotlib.use('Agg')

API_BASE_URL = os.getenv('API_BASE_URL', 'http://backend:8000').rstrip('/')


def api_get(path: str, **kwargs):
    response = requests.get(f'{API_BASE_URL}{path}', timeout=15, **kwargs)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict):
    response = requests.post(f'{API_BASE_URL}{path}', json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def api_delete(path: str):
    response = requests.delete(f'{API_BASE_URL}{path}', timeout=15)
    response.raise_for_status()
    return response.json()


def to_iso_utc(dt: datetime) -> str:
    dt_utc = dt.replace(tzinfo=timezone.utc, microsecond=0)
    return dt_utc.isoformat().replace('+00:00', 'Z')


def clean_query_params(raw_params: dict) -> dict:
    cleaned = {}
    for key, value in raw_params.items():
        if value is None:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped or stripped.lower() == 'none':
                continue
            cleaned[key] = stripped
            continue
        cleaned[key] = value
    return cleaned


st.set_page_config(page_title='SpendFlow Dashboard', page_icon='💸', layout='wide')
st.title('SpendFlow Frontend (Streamlit)')
st.caption('Тонкий клиент: UI работает только через HTTP API backend (FastAPI).')

rules = {
    'thresholds': {
        'max_total_budget': 100000,
        'max_category_budget': {
            'Transport': 5000,
            'Food': 7000,
            'Leisure': 6000,
            'Shopping': 8000,
            'Bills': 9000,
        },
    }
}

categories = ['Transport', 'Food', 'Leisure', 'Shopping', 'Bills']

with st.sidebar:
    st.subheader('Параметры')
    description = st.text_input('Описание траты', value='Uber ride')
    amount = st.number_input('Сумма', min_value=0.0, value=1000.0, step=100.0)
    category = st.selectbox('Категория', options=categories)
    category_total = st.number_input('Сумма по категории до операции', min_value=0.0, value=0.0, step=100.0)
    total_spent = st.number_input('Общая сумма до операции', min_value=0.0, value=0.0, step=100.0)
    is_budget_exceeded = st.checkbox('Бюджет уже превышен', value=False)
    tags_input = st.text_input('Теги (через запятую)', value='')

    st.markdown('---')
    st.subheader('Управление бюджетом')
    budget_month = st.number_input('Месяц лимита', min_value=1, max_value=12, value=date.today().month, step=1)
    budget_year = st.number_input('Год лимита', min_value=2000, max_value=2100, value=date.today().year, step=1)
    budget_category = st.selectbox('Категория лимита', options=categories, key='budget_category')
    budget_amount = st.number_input('Лимит категории (₸)', min_value=1.0, value=10000.0, step=500.0)
    if st.button('Сохранить лимит', use_container_width=True):
        budget_payload = {
            'category_name': budget_category,
            'limit_amount': budget_amount,
            'month': int(budget_month),
            'year': int(budget_year),
        }
        budget_row = api_post('/api/v1/budgets', budget_payload)
        st.success(
            f"Лимит сохранён: {budget_row['category_name']} {budget_row['month']:02d}.{budget_row['year']} = "
            f"{budget_row['limit_amount']:,.0f} ₸".replace(',', ' ')
        )


col1, col2 = st.columns(2)

with col1:
    st.subheader('Проверка правил')
    if st.button('Запустить проверку'):
        payload = {
            'description': description,
            'amount': amount,
            'category': category,
            'category_total': category_total,
            'total_spent': total_spent,
            'is_budget_exceeded': is_budget_exceeded,
            'tags_list': [tag.strip() for tag in tags_input.split(',') if tag.strip()],
        }
        result = api_post('/api/v1/rules/check', payload)
        st.info(result['result'])

    st.subheader('Рекомендации')
    if st.button('Получить рекомендации'):
        category_limits = rules['thresholds']['max_category_budget']
        category_totals = {k: 0.0 for k in category_limits}
        category_totals[category] = category_total + amount
        result = api_post(
            '/api/v1/recommendations',
            {
                'current_total': total_spent + amount,
                'total_limit': rules['thresholds']['max_total_budget'],
                'category_totals': category_totals,
                'category_limits': category_limits,
                'current_transaction_amount': amount,
                'current_category': category,
            },
        )
        for rec in result['recommendations']:
            st.write(f'- {rec}')

    st.subheader('Анализ аномалий')
    if st.button('Проверить аномалию'):
        result = api_post('/api/v1/anomalies/score', {'amount': amount, 'category': category})
        st.write(f"Статус: {result['label']} (score={result['score']:.3f})")

with col2:
    st.subheader('Прогноз')
    total_limit = float(rules['thresholds']['max_total_budget'])
    forecast_data = api_get('/api/v1/forecast', params={'total_limit': total_limit})
    probability_data = api_get(
        '/api/v1/forecast/probability',
        params={
            'total_spent': total_spent + amount,
            'total_limit': total_limit,
        },
    )

    st.metric('Прогноз на следующий месяц', f"{forecast_data['forecast']:,.0f} ₸".replace(',', ' '))
    st.metric('Вероятность уложиться в бюджет', f"{probability_data['probability']:.0f}%")
    st.caption(probability_data['explanation'])
    if forecast_data.get('chart_data', {}).get('message'):
        st.info(forecast_data['chart_data']['message'])

    chart_data = forecast_data['chart_data']
    fig, ax = plt.subplots(figsize=(8, 3))
    months = chart_data.get('months', [])
    actual = chart_data.get('actual', [])
    forecast_value = float(chart_data.get('forecast', 0.0))
    series = [*actual, forecast_value] if months else []
    colors = ['#3B82F6'] * max(len(series) - 1, 0) + (['#F97316'] if series else [])
    ax.bar(months, series, label='Факт/Прогноз', color=colors)
    ax.axhline(y=chart_data['limit'], color='red', linestyle='--', label='Лимит')
    if months:
        ax.text(months[-1], forecast_value, f" {months[-1]}", va='bottom', ha='left')
    ax.legend()
    st.pyplot(fig, use_container_width=True)

    st.subheader('Состояние лимитов (Top-3)')
    budget_rows = api_get('/api/v1/budgets', params={'month': date.today().month, 'year': date.today().year})
    budget_rows_sorted = sorted(budget_rows, key=lambda r: float(r.get('usage_ratio', 0.0)), reverse=True)[:3]
    if budget_rows_sorted:
        for row in budget_rows_sorted:
            ratio = float(row.get('usage_ratio', 0.0))
            spent = float(row.get('spent_amount', 0.0))
            limit_amount = float(row.get('limit_amount', 0.0))
            if ratio >= 0.9:
                st.markdown(
                    f":red[**{row['category_name']}** — {spent:,.0f}/{limit_amount:,.0f} ₸ ({ratio * 100:.0f}%)]".replace(',', ' ')
                )
            else:
                st.markdown(
                    f"**{row['category_name']}** — {spent:,.0f}/{limit_amount:,.0f} ₸ ({ratio * 100:.0f}%)".replace(',', ' ')
                )
            st.progress(min(max(ratio, 0.0), 1.0))
    else:
        st.info('Для текущего месяца лимиты пока не заданы.')


st.subheader('CRUD транзакций')
crud_col1, crud_col2 = st.columns([1, 1.2])

with crud_col1:
    st.markdown('**Создание транзакции**')
    if st.button('Сохранить транзакцию в БД'):
        payload = {
            'description': description,
            'amount': amount,
            'category': category,
            'tags': [tag.strip() for tag in tags_input.split(',') if tag.strip()],
        }
        created = api_post('/api/v1/transactions', payload)
        st.success(f"Создана запись id={created['id']}")
        if created.get('limit_warning'):
            st.warning(created.get('warning_message') or 'Лимит категории превышен.')

    st.markdown('**Удаление транзакции**')
    tx_id_to_delete = st.number_input('ID для удаления', min_value=1, value=1, step=1)
    if st.button('Удалить транзакцию'):
        result = api_delete(f'/api/v1/transactions/{int(tx_id_to_delete)}')
        if result['deleted']:
            st.success('Удалено')
        else:
            st.warning('Не найдено')

with crud_col2:
    st.markdown('**История транзакций**')
    period_on = st.checkbox('Фильтровать по периоду', value=False)
    date_from = date_to = None
    if period_on:
        dr = st.date_input('Период', value=(date.today().replace(day=1), date.today()))
        if isinstance(dr, tuple) and len(dr) == 2:
            date_from = to_iso_utc(datetime.combine(dr[0], time.min))
            date_to = to_iso_utc(datetime.combine(dr[1], time.max))

    params = {'limit': 200}
    if date_from:
        params['date_from'] = date_from
    if date_to:
        params['date_to'] = date_to
    params = clean_query_params(params)

    sum_params = {}
    if date_from:
        sum_params['date_from'] = date_from
    if date_to:
        sum_params['date_to'] = date_to
    sum_params = clean_query_params(sum_params)

    rows = api_get('/api/v1/transactions', params=params)
    total = api_get('/api/v1/transactions/sum', params=sum_params)['total']
    st.caption(f"Сумма по фильтру: {total:,.0f} ₸".replace(',', ' '))

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info('Пока нет транзакций.')
