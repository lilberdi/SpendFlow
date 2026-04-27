FROM python:3.13-slim AS base

# Отключаем создание .pyc и включаем буферизацию логов
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Устанавливаем системные зависимости
# Мы оставили libgl1 и libglib2.0-0, которые подошли для Trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Обновляем pip и копируем файл зависимостей
RUN pip install --no-cache-dir --upgrade pip
COPY requirements.txt .

# Устанавливаем библиотеки напрямую из requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код
COPY . .

FROM base AS backend
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS frontend
EXPOSE 8501
CMD ["streamlit", "run", "frontend/main.py", "--server.port=8501", "--server.address=0.0.0.0"]