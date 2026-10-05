"""Connection pool và settings. API kết nối bằng role api_reader: chỉ SELECT trên analytics + meta."""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import URL, Connection, create_engine

DB_URL = URL.create(
    "postgresql+psycopg",
    username=os.environ.get("API_DB_USER", "api_reader"),
    password=os.environ.get("API_READER_PASSWORD", "change_me"),
    host=os.environ.get("POSTGRES_HOST", "localhost"),
    port=int(os.environ.get("POSTGRES_PORT", "5432")),
    database=os.environ.get("POSTGRES_DB", "qtdl"),
)

engine = create_engine(DB_URL, pool_size=5, max_overflow=5, pool_pre_ping=True)

# Schema được phép hiện trong catalog (chỉ metadata: tên, kiểu, comment — không đọc dữ liệu).
CATALOG_SCHEMAS = ("raw", "staging", "core", "analytics", "meta")


def get_conn() -> Iterator[Connection]:
    with engine.connect() as conn:
        yield conn
