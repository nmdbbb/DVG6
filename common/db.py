"""Kết nối Postgres dùng chung cho scripts, ingestion và quality.

Mỗi tầng kết nối bằng đúng role của nó (db/roles.sql):
- admin      : migration, reset (POSTGRES_USER)
- etl_writer : ingestion, transform, quality
- api_reader : API (xem api/deps.py)
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
