"""Shared helpers for reproducible, read-only analysis notebooks."""

from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Sequence
from typing import Any

import polars as pl
import psycopg
from dotenv import load_dotenv


def find_project_dir(start: Path | None = None) -> Path:
    """Find the DVG6 root from the notebook's current working directory."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "Makefile").is_file() and (candidate / "transform").is_dir():
            return candidate
    raise FileNotFoundError("Không tìm thấy thư mục gốc DVG6 (cần Makefile và transform/).")


PROJECT_DIR = find_project_dir()
load_dotenv(PROJECT_DIR / ".env", override=False)


def connect() -> psycopg.Connection:
    """Connect to the local Docker PostgreSQL using the read-only analyst role."""
    password = os.environ.get("ANALYST_PASSWORD")
    if not password:
        raise RuntimeError("Thiếu ANALYST_PASSWORD trong DVG6/.env.")
    return psycopg.connect(
        host="localhost",
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "qtdl"),
        user="analyst",
        password=password,
    )


def query_df(query: str, params: Sequence[Any] | None = None) -> pl.DataFrame:
    """Run a read-only SQL query and return a Polars DataFrame."""
    with connect() as connection:
        if params is None:
            return pl.read_database(query, connection)
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [description.name for description in cursor.description]
        if not rows:
            return pl.DataFrame(schema=columns)
        return pl.DataFrame(rows, schema=columns, orient="row")


def available_core_relations() -> set[str]:
    rows = query_df(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'core'
        """
    )
    return set(rows.get_column("table_name").to_list())


def require_core_relations(*names: str) -> None:
    available = available_core_relations()
    missing = sorted(set(names) - available)
    if missing:
        raise RuntimeError(
            "Thiếu relation trong schema core: "
            + ", ".join(missing)
            + ". Cần bổ sung/chạy model dbt tương ứng trước khi chạy notebook này."
        )


def require_nonempty_core(table: str) -> None:
    # table is selected from notebook constants, not user input.
    with connect() as connection:
        count = connection.execute(f'SELECT COUNT(*) FROM core."{table}"').fetchone()[0]
    if count == 0:
        raise RuntimeError(
            f"core.{table} đang rỗng. Kiểm tra ingestion, transform và quality trước khi EDA."
        )


REPORTS_DIR = PROJECT_DIR / "analysis" / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
TABLES_DIR = REPORTS_DIR / "tables"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
TABLES_DIR.mkdir(parents=True, exist_ok=True)


def save_csv(frame: pl.DataFrame, filename: str) -> Path:
    path = TABLES_DIR / filename
    frame.write_csv(path)
    return path
