FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.0

COPY pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY . .

# Бот — просто Python скрипт, запускаем main.py
CMD ["python", "main.py"]