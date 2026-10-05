"""Ghi bản ghi của một connector vào raw và ghi nhật ký lô vào meta.ingestion_batch.

Vòng đời một lô:
1. Tạo dòng meta.ingestion_batch status='running', source_mode=live|mock (commit ngay để lô chết
   giữa chừng vẫn có vết).
2. Mode live: lưu từng trang gốc xuống data/raw/<source>/<ngày>/<batch_id>/ TRƯỚC khi parse,
   cộng manifest.json. mock_server phát lại chính các file này.
3. Parse trang, ghi từng khối vào bảng raw kèm _batch_id; trùng _row_hash với lô trước thì bỏ qua.
   Mọi _row_hash lô đã thấy ghi vào meta.ingestion_batch_row (kể cả bản ghi đã có sẵn).
4. Cập nhật status='success' + row_count, hoặc 'failed' + error_message.
5. Lô fail giữ nguyên dòng đã ghi; staging chỉ đọc lô success nên tự bỏ qua.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime

from psycopg import sql
from psycopg.types.json import Jsonb

from common.db import REPO_ROOT, connect
from ingestion.base import Connector, RawPage, SourceMode

CHUNK_SIZE = 1000
RAW_DIR = REPO_ROOT / "data" / "raw"


@dataclass
class BatchResult:
    batch_id: str | None
    source: str
    mode: str
    status: str
    rows_fetched: int
    row_count: int
    snapshot_dir: str | None


class SnapshotWriter:
    """Bản gốc của một lô live: page_00001.json|html ... + manifest.json."""

    def __init__(self, source: str, batch_id: str, params: dict):
        self.dir = RAW_DIR / source / date.today().isoformat() / batch_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.meta = {
            "source": source,
            "batch_id": batch_id,
            "mode": "live",
            "params": params,
            "started_at": _now(),
            "pages": [],
        }

    def write(self, page: RawPage) -> None:
        name = f"page_{len(self.meta['pages']) + 1:05d}{page.suffix}"
        (self.dir / name).write_bytes(page.content)
        self.meta["pages"].append(
            {
                "file": name,
                "url": page.url,
                "content_type": page.content_type,
                "bytes": len(page.content),
                "sha256": hashlib.sha256(page.content).hexdigest(),
            }
        )

    def finish(self, complete: bool, record_count: int) -> None:
        # record_count: số bản ghi loader thực sự dùng (khác tổng trong trang khi chạy --limit).
        self.meta.update(finished_at=_now(), complete=complete, record_count=record_count)
        (self.dir / "manifest.json").write_text(
            json.dumps(self.meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @property
    def rel(self) -> str:
        return str(self.dir.relative_to(REPO_ROOT)).replace("\\", "/")


def _now() -> str:
    return datetime.now(UTC).isoformat()


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


def _records(
    connector: Connector, since: date | None, mode: SourceMode, limit: int | None, on_page
):
    """Duyệt trang -> bản ghi, dừng ở limit. on_page(page) chạy trước khi parse trang đó."""
    n = 0
    for page in connector.fetch(since, mode):
        on_page(page)
        for rec in connector.records(page):
            if limit is not None and n >= limit:
                return
            n += 1
            yield rec
        if limit is not None and n >= limit:
            return


def run(
    connector: Connector,
    since: date | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    mode: SourceMode = "live",
) -> BatchResult:
    if dry_run:
        n = sum(1 for _ in _records(connector, since, mode, limit, on_page=lambda p: None))
        return BatchResult(None, connector.name, mode, "dry-run", n, 0, None)

    batch_id = str(uuid.uuid4())
    params = {"since": since.isoformat() if since else None, "limit": limit}
    schema, table = connector.raw_table.split(".")
    cols = [*connector.columns, "_batch_id", "_source_name", "_row_hash", "_payload"]
    insert_raw = sql.SQL(
        "insert into {table} ({cols}) values ({vals}) on conflict (_row_hash) do nothing"
    ).format(
        table=sql.Identifier(schema, table),
        cols=sql.SQL(", ").join(map(sql.Identifier, cols)),
        vals=sql.SQL(", ").join(sql.Placeholder() * len(cols)),
    )
    insert_seen = (
        "insert into meta.ingestion_batch_row (batch_id, row_hash) values (%s, %s) "
        "on conflict do nothing"
    )

    with connect("etl_writer") as conn:
        _register_source(conn, connector)
        conn.execute(
            "insert into meta.ingestion_batch (batch_id, source_name, status, params, source_mode) "
            "values (%s, %s, 'running', %s, %s)",
            (batch_id, connector.name, Jsonb(params), mode),
        )
        conn.commit()

        snapshot = SnapshotWriter(connector.name, batch_id, params) if mode == "live" else None
        stats = {"bytes": 0, "fetched": 0}

        def on_page(page: RawPage) -> None:
            stats["bytes"] += len(page.content)
            if snapshot:
                snapshot.write(page)  # bản gốc xuống đĩa TRƯỚC khi parse

        def flush(chunk: list[dict]) -> None:
            if not chunk:
                return
            hashes = [connector.row_hash(rec) for rec in chunk]
            with conn.cursor() as cur:
                cur.executemany(
                    insert_raw,
                    [
                        (
                            *(_as_text(rec.get(c)) for c in connector.columns),
                            batch_id,
                            connector.name,
                            h,
                            Jsonb(rec),
                        )
                        for rec, h in zip(chunk, hashes, strict=True)
                    ],
                )
                cur.executemany(insert_seen, [(batch_id, h) for h in hashes])
            conn.commit()

        try:
            chunk: list[dict] = []
            for rec in _records(connector, since, mode, limit, on_page):
                chunk.append(rec)
                stats["fetched"] += 1
                if len(chunk) >= CHUNK_SIZE:
                    flush(chunk)
                    chunk = []
            flush(chunk)

            row_count = conn.execute(
                sql.SQL("select count(*) from {} where _batch_id = %s").format(
                    sql.Identifier(schema, table)
                ),
                (batch_id,),
            ).fetchone()[0]
            conn.execute(
                "update meta.ingestion_batch set status = 'success', finished_at = now(), "
                "rows_fetched = %s, row_count = %s, bytes = %s where batch_id = %s",
                (stats["fetched"], row_count, stats["bytes"], batch_id),
            )
            conn.commit()
            if snapshot:
                snapshot.finish(complete=True, record_count=stats["fetched"])
        except Exception as exc:
            conn.rollback()
            conn.execute(
                "update meta.ingestion_batch set status = 'failed', finished_at = now(), "
                "rows_fetched = %s, bytes = %s, error_message = %s where batch_id = %s",
                (stats["fetched"], stats["bytes"], f"{type(exc).__name__}: {exc}"[:2000], batch_id),
            )
            conn.commit()
            if snapshot:
                snapshot.finish(complete=False, record_count=stats["fetched"])
            raise

    return BatchResult(
        batch_id,
        connector.name,
        mode,
        "success",
        stats["fetched"],
        row_count,
        snapshot.rel if snapshot else None,
    )


def _as_text(value) -> str | None:
    # Raw giữ mọi thứ dạng text; chỉ None mới thành NULL.
    if value is None:
        return None
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
