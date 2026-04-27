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
            'Food': 3000,
            'Shopping': 2000,
            'Entertainment': 1500,
            'Other': 1000,
        },
    }
}

categories = ['Transport', 'Food', 'Shopping', 'Entertainment', 'Other']

with st.sidebar:
    st.subheader('Параметры')
    description = st.text_input('Описание траты', value='Uber ride')
    amount = st.number_input('Сумма', min_value=0.0, value=1000.0, step=100.0)
    category = st.selectbox('Категория', options=categories)
    category_total = st.number_input('Сумма по категории до операции', min_value=0.0, value=0.0, step=100.0)
    total_spent = st.number_input('Общая сумма до операции', min_value=0.0, value=0.0, step=100.0)
    is_budget_exceeded = st.checkbox('Бюджет уже превышен', value=False)
    tags_input = st.text_input('Теги (через запятую)', value='')


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

    chart_data = forecast_data['chart_data']
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.bar(chart_data['months'][:-1], chart_data['actual'], label='Факт')
    ax.bar(chart_data['months'][-1], chart_data['forecast'], label='Прогноз', color='orange')
    ax.axhline(y=chart_data['limit'], color='red', linestyle='--', label='Лимит')
    ax.legend()
    st.pyplot(fig, use_container_width=True)


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
