"""Data dictionary sinh từ COMMENT ON trong Postgres (migration + persist_docs của dbt).

Chỉ đọc pg_catalog (metadata) và meta.*_profile; không SELECT dữ liệu của raw/staging/core.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection, text

from api.deps import CATALOG_SCHEMAS, get_conn
from api.schemas.catalog import Column, Table
from api.schemas.common import Envelope, envelope

router = APIRouter(prefix="/catalog", tags=["catalog"])

LATEST_TABLE_PROFILE = """
    select * from meta.table_profile
    where run_id = (select run_id from meta.table_profile order by profiled_at desc limit 1)
"""


@router.get("/tables", response_model=Envelope[list[Table]])
def tables(
    schema: str | None = Query(None, description="raw | staging | core | analytics | meta"),
    conn: Connection = Depends(get_conn),
):
    rows = (
        conn.execute(
            text(
                f"""
            with p as ({LATEST_TABLE_PROFILE})
            select n.nspname as schema_name, c.relname as table_name,
                   case c.relkind when 'v' then 'view' when 'm' then 'materialized view'
                                  else 'table' end as kind,
                   obj_description(c.oid, 'pg_class') as comment,
                   (select count(*) from pg_attribute a
                    where a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped) as column_count,
                   p.row_count, p.profiled_at
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            left join p on p.schema_name = n.nspname and p.table_name = c.relname
            where n.nspname = any(:schemas)
              and c.relkind in ('r', 'v', 'm', 'p')
              and (cast(:schema as text) is null or n.nspname = :schema)
            order by array_position(cast(:schemas as text[]), n.nspname::text), c.relname
            """
            ),
            {"schemas": list(CATALOG_SCHEMAS), "schema": schema},
        )
        .mappings()
        .all()
    )
    as_of = max((r["profiled_at"] for r in rows if r["profiled_at"]), default=None)
    return envelope([dict(r) for r in rows], "pg_catalog, meta.table_profile", as_of)


@router.get("/tables/{name}/columns", response_model=Envelope[list[Column]])
def columns(name: str, conn: Connection = Depends(get_conn)):
    """`name` dạng `schema.table`, ví dụ `core.fct_main`."""
    schema, _, table = name.partition(".")
    if schema not in CATALOG_SCHEMAS or not table:
        raise HTTPException(404, f"Không có bảng {name}")

    rows = (
        conn.execute(
            text(
                """
            with cp as (
                select * from meta.column_profile
                where schema_name = :schema and table_name = :table
                  and run_id = (select run_id from meta.column_profile
                                where schema_name = :schema and table_name = :table
                                order by profiled_at desc limit 1)
            )
            select a.attnum as position, a.attname as column_name,
                   format_type(a.atttypid, a.atttypmod) as data_type,
                   not a.attnotnull as nullable,
                   col_description(c.oid, a.attnum) as comment,
                   cp.null_count, cp.null_rate, cp.profiled_at
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            join pg_attribute a on a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
            left join cp on cp.column_name = a.attname
            where n.nspname = :schema and c.relname = :table and c.relkind in ('r', 'v', 'm', 'p')
            order by a.attnum
            """
            ),
            {"schema": schema, "table": table},
        )
        .mappings()
        .all()
    )
    if not rows:
        raise HTTPException(404, f"Không có bảng {name}")
    as_of = next((r["profiled_at"] for r in rows if r["profiled_at"]), None)
    return envelope([dict(r) for r in rows], "pg_catalog, meta.column_profile", as_of)
