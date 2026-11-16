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

# pg_dump/psql cho `make publish` và `make psql`. Debian trixie (base của python:3.11-slim) có
# sẵn client 17: dump được server 16 (local) và nạp được vào 17 (Neon/Supabase).
# Build fail ở đây nghĩa là base image đã đổi sang bản Debian có client cũ hơn 16 — khi đó
# phải thêm kho apt.postgresql.org đúng codename, vì pg_dump 15 không dump nổi server 16.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends postgresql-client; \
    rm -rf /var/lib/apt/lists/*; \
    pg_dump --version | grep -qE ' 1[6-9]| [2-9][0-9]'

COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml --extra dev

# Mã nguồn được mount vào /app lúc chạy (docker-compose.yml) để sửa code không cần build lại.
COPY . .
