# Mọi lệnh chạy trong Docker: máy chỉ cần git + Docker + make.
# Recipe chỉ gọi `docker compose`, không dùng cú pháp riêng của bash, nên chạy được cả trên Windows.

COMPOSE := docker compose
ETL     := $(COMPOSE) run --rm $(RUN_FLAGS) etl
SOURCE  ?=
# live | mock. Để trống thì lấy SOURCE_MODE trong .env, không có thì live.
SOURCE_MODE ?=
# CI đặt RUN_FLAGS=-T (không có TTY)
RUN_FLAGS ?=

ifneq ($(SOURCE_MODE),)
MODE_ENV := -e SOURCE_MODE=$(SOURCE_MODE)
endif
ETL_INGEST := $(COMPOSE) run --rm $(RUN_FLAGS) $(MODE_ENV) etl

.PHONY: help up down build migrate ingest transform quality test lint dashboard all reset lineage demo-break psql logs mock mock-check

help:
	@echo make up         - khoi dong Postgres, cho healthy, build image Python
	@echo make migrate    - ap dung migration chua chay + cap quyen role
	@echo make ingest     - chay toan bo connector (SOURCE=source_demo, SOURCE_MODE=live/mock)
	@echo make mock       - chay mock server tai http://localhost:8001
	@echo make mock-check - ingest live roi mock, so khop so dong va _row_hash
	@echo make transform  - dbt run: staging, core, analytics
	@echo make quality    - dbt test + quality rules, exit 1 neu co check error fail
	@echo make test       - pytest
	@echo make dashboard  - chay api :8000 + web :5173
	@echo make all        - up, migrate, ingest, transform, quality
	@echo make reset      - xoa sach warehouse roi dung lai tu so khong
	@echo make lineage    - dbt docs tai http://localhost:8080
	@echo make demo-break - co tinh lam hong du lieu de chung minh quality chan pipeline

up:
	$(COMPOSE) up -d --wait db mock_server
	$(COMPOSE) build etl

down:
	$(COMPOSE) --profile cli --profile tools down

build:
	$(COMPOSE) build etl web

migrate:
	$(ETL) python -m scripts.migrate

ingest:
ifeq ($(SOURCE),)
	$(ETL_INGEST) python -m ingestion.cli run-all
else
	$(ETL_INGEST) python -m ingestion.cli run --source $(SOURCE)
endif

mock:
	$(COMPOSE) up -d --wait mock_server
	@echo Mock server: http://localhost:8001

# Nghiem thu duong du phong: hai lo phai trung so dong va tap _row_hash.
mock-check:
	$(MAKE) ingest SOURCE=$(or $(SOURCE),source_demo) SOURCE_MODE=live
	$(MAKE) ingest SOURCE=$(or $(SOURCE),source_demo) SOURCE_MODE=mock
	$(ETL) python -m scripts.compare_batches --source $(or $(SOURCE),source_demo)

transform:
	$(ETL) dbt run

quality:
	$(ETL) python -m quality.runner --with-dbt

test:
	$(ETL) pytest -q

lint:
	$(ETL) ruff check .
	$(ETL) black --check .

dashboard:
	$(COMPOSE) up -d --build --wait api web
	@echo Dashboard: http://localhost:5173  -  API docs: http://localhost:8000/docs

all: up migrate ingest transform quality

reset: up
	$(ETL) python -m scripts.reset_db
	$(MAKE) migrate ingest transform quality

lineage:
	$(COMPOSE) run --rm --service-ports etl sh -c "dbt docs generate && dbt docs serve --host 0.0.0.0 --port 8080 --no-browser"

demo-break:
	$(ETL) python -m scripts.demo_break

psql:
	$(COMPOSE) exec db psql -U qtdl -d qtdl

logs:
	$(COMPOSE) logs -f api web
