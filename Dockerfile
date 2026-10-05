# Image Python dùng chung cho service etl (ingestion, dbt, quality, migrate) và api.
# Một image cho cả hai để mọi người chạy đúng một bộ dependency.
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DBT_PROFILES_DIR=/app/transform \
    DBT_PROJECT_DIR=/app/transform

WORKDIR /app

COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml --extra dev

# Mã nguồn được mount vào /app lúc chạy (docker-compose.yml) để sửa code không cần build lại.
COPY . .
