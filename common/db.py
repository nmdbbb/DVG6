"""Kết nối Postgres dùng chung cho scripts, ingestion và quality.

Mỗi tầng kết nối bằng đúng role của nó (db/roles.sql):
- admin      : migration, reset (POSTGRES_USER)
- etl_writer : ingestion, transform, quality
- api_reader : API (xem api/deps.py)

Mọi lệnh ở đây chạy trên warehouse **local**. Kho dùng chung (decision #35) chỉ nhận dữ liệu
qua `scripts/publish.py`; không lệnh nào khác được trỏ vào đó.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

REPO_ROOT = Path(__file__).resolve().parent.parent

_ROLE_PASSWORD_ENV = {
    "etl_writer": "ETL_WRITER_PASSWORD",
    "api_reader": "API_READER_PASSWORD",
    "analyst": "ANALYST_PASSWORD",
}

# Host được coi là warehouse local. "db" là tên service trong docker-compose.yml.
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "db", ""})


def is_local_host(host: str) -> bool:
    return host.strip().lower() in LOCAL_HOSTS


def assert_local(action: str) -> None:
    """Dừng nếu POSTGRES_HOST không phải warehouse local.

    Chặn tai nạn kiểu đặt POSTGRES_HOST trỏ vào kho dùng chung rồi chạy `make reset` —
    một lệnh xóa sạch dữ liệu của cả nhóm.
    """
    host = os.environ.get("POSTGRES_HOST", "localhost")
    if not is_local_host(host):
        raise SystemExit(
            f"TỪ CHỐI: '{action}' chỉ được chạy trên warehouse local, nhưng POSTGRES_HOST={host!r}.\n"
            "Kho dùng chung chỉ nhận dữ liệu qua `make publish`. Xem docs/runbook.md."
        )


def conninfo(role: str = "admin") -> str:
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("POSTGRES_DB", "qtdl")
    if role == "admin":
        user = os.environ.get("POSTGRES_USER", "qtdl")
        password = os.environ.get("POSTGRES_PASSWORD", "change_me")
    else:
        user = role
        password = os.environ.get(_ROLE_PASSWORD_ENV[role], "change_me")
    return psycopg.conninfo.make_conninfo(
        host=host, port=port, dbname=dbname, user=user, password=password
    )


def connect(role: str = "admin", autocommit: bool = False) -> psycopg.Connection:
    return psycopg.connect(conninfo(role), autocommit=autocommit)
