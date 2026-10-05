"""Ghi bản ghi của một connector vào raw và ghi nhật ký lô vào meta.ingestion_batch.

Vòng đời một lô:
1. Tạo dòng meta.ingestion_batch status='running' (commit ngay để lô chết giữa chừng vẫn có vết).
2. Lưu bản gốc xuống data/raw/<source>/<ngày>/<batch_id>.jsonl.
3. Ghi từng khối vào bảng raw kèm _batch_id; trùng _row_hash với lô trước thì bỏ qua.
4. Cập nhật status='success' + row_count, hoặc 'failed' + error_message.
5. Lô fail giữ nguyên dòng đã ghi; staging chỉ đọc lô success nên tự bỏ qua.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import date
from itertools import islice
from pathlib import Path

from psycopg import sql
from psycopg.types.json import Jsonb

from common.db import REPO_ROOT, connect
from ingestion.base import Connector

CHUNK_SIZE = 1000
RAW_DIR = REPO_ROOT / "data" / "raw"


@dataclass
class BatchResult:
    batch_id: str | None
    source: str
    status: str
    rows_fetched: int
    row_count: int
    raw_file: str | None


def _archive(connector: Connector, batch_id: str, records: list[dict]) -> Path:
    folder = RAW_DIR / connector.name / date.today().isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{batch_id}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def _register_source(conn, connector: Connector) -> None:
    meta = connector.describe()
    conn.execute(
        """
        insert into meta.source (source_name, description, url, license, update_frequency, owner)
        values (%(name)s, %(description)s, %(url)s, %(license)s, %(update_frequency)s, %(owner)s)
        on conflict (source_name) do update set
            description = excluded.description, url = excluded.url, license = excluded.license,
            update_frequency = excluded.update_frequency, owner = excluded.owner
        """,
        {"name": connector.name, **asdict(meta)},
    )


def run(
    connector: Connector,
    since: date | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> BatchResult:
    records = list(islice(connector.fetch(since), limit))

    if dry_run:
        return BatchResult(None, connector.name, "dry-run", len(records), 0, None)

    batch_id = str(uuid.uuid4())
    params = {"since": since.isoformat() if since else None, "limit": limit}
    schema, table = connector.raw_table.split(".")
    cols = [*connector.columns, "_batch_id", "_source_name", "_row_hash", "_payload"]
    insert = sql.SQL(
        "insert into {table} ({cols}) values ({vals}) on conflict (_row_hash) do nothing"
    ).format(
        table=sql.Identifier(schema, table),
        cols=sql.SQL(", ").join(map(sql.Identifier, cols)),
        vals=sql.SQL(", ").join(sql.Placeholder() * len(cols)),
    )

    with connect("etl_writer") as conn:
        _register_source(conn, connector)
        conn.execute(
            "insert into meta.ingestion_batch (batch_id, source_name, status, params) "
            "values (%s, %s, 'running', %s)",
            (batch_id, connector.name, Jsonb(params)),
        )
        conn.commit()

        try:
            raw_file = _archive(connector, batch_id, records)
            with conn.cursor() as cur:
                for start in range(0, len(records), CHUNK_SIZE):
                    chunk = records[start : start + CHUNK_SIZE]
                    cur.executemany(
                        insert,
                        [
                            (
                                *(_as_text(rec.get(c)) for c in connector.columns),
                                batch_id,
                                connector.name,
                                connector.row_hash(rec),
                                Jsonb(rec),
                            )
                            for rec in chunk
                        ],
                    )
                    conn.commit()

            row_count = conn.execute(
                sql.SQL("select count(*) from {} where _batch_id = %s").format(
                    sql.Identifier(schema, table)
                ),
                (batch_id,),
            ).fetchone()[0]
            conn.execute(
                "update meta.ingestion_batch set status = 'success', finished_at = now(), "
                "rows_fetched = %s, row_count = %s, bytes = %s where batch_id = %s",
                (len(records), row_count, raw_file.stat().st_size, batch_id),
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            conn.execute(
                "update meta.ingestion_batch set status = 'failed', finished_at = now(), "
                "rows_fetched = %s, error_message = %s where batch_id = %s",
                (len(records), f"{type(exc).__name__}: {exc}"[:2000], batch_id),
            )
            conn.commit()
            raise

    return BatchResult(
        batch_id,
        connector.name,
        "success",
        len(records),
        row_count,
        str(raw_file.relative_to(REPO_ROOT)),
    )


def _as_text(value) -> str | None:
    # Raw giữ mọi thứ dạng text; chỉ None mới thành NULL.
    if value is None:
        return None
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
