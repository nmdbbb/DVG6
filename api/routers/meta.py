"""Sức khỏe pipeline: nguồn, lô nạp, kết quả quality, số dòng từng tầng. Đọc schema meta."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection, text

from api.deps import get_conn
from api.schemas.common import Envelope, envelope
from api.schemas.meta import Batch, LayerTable, QualityCheck, QualityRun, Source

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/sources", response_model=Envelope[list[Source]])
def sources(conn: Connection = Depends(get_conn)):
    rows = (
        conn.execute(
            text(
                """
            select s.source_name, s.description, s.url, s.license, s.update_frequency, s.owner,
                   count(b.batch_id)                                          as batch_count,
                   coalesce(sum(b.row_count) filter (where b.status = 'success'), 0) as total_rows,
                   max(b.started_at)                                          as last_batch_at,
                   (array_agg(b.status order by b.started_at desc))[1]        as last_status
            from meta.source s
            left join meta.ingestion_batch b using (source_name)
            group by s.source_name
            order by s.source_name
            """
            )
        )
        .mappings()
        .all()
    )
    as_of = max((r["last_batch_at"] for r in rows if r["last_batch_at"]), default=None)
    return envelope([dict(r) for r in rows], "meta.source, meta.ingestion_batch", as_of)


@router.get("/batches", response_model=Envelope[list[Batch]])
def batches(
    source: str | None = Query(None, description="Lọc theo tên nguồn."),
    status: Literal["running", "success", "failed"] | None = Query(None),
    mode: Literal["live", "mock"] | None = Query(None, description="Lọc theo đường lấy dữ liệu."),
    limit: int = Query(100, ge=1, le=1000),
    conn: Connection = Depends(get_conn),
):
    rows = (
        conn.execute(
            text(
                """
            select batch_id, source_name, source_mode, started_at, finished_at, status, rows_fetched,
                   row_count, bytes, error_message,
                   extract(epoch from finished_at - started_at)::float as duration_seconds
            from meta.ingestion_batch
            where (cast(:source as text) is null or source_name = :source)
              and (cast(:status as text) is null or status = :status)
              and (cast(:mode as text) is null or source_mode = :mode)
            order by started_at desc
            limit :limit
            """
            ),
            {"source": source, "status": status, "mode": mode, "limit": limit},
        )
        .mappings()
        .all()
    )
    as_of = rows[0]["started_at"] if rows else None
    return envelope([dict(r) for r in rows], "meta.ingestion_batch", as_of)


@router.get("/quality", response_model=Envelope[list[QualityCheck]])
def quality(
    status: Literal["all", "failed", "passed"] = Query("all"),
    run_id: str | None = Query(None, description="Mặc định: lần chạy mới nhất."),
    conn: Connection = Depends(get_conn),
):
    rows = (
        conn.execute(
            text(
                """
            with target as (
                select coalesce(
                    cast(:run_id as uuid),
                    (select run_id from meta.quality_run order by ran_at desc limit 1)
                ) as run_id
            )
            select q.run_id, q.check_name, q.check_source, q.severity, q.passed,
                   q.observed_value, q.threshold, q.message, q.ran_at
            from meta.quality_run q join target t using (run_id)
            where :status = 'all' or (:status = 'failed') = not q.passed
            order by q.passed, q.severity, q.check_name
            """
            ),
            {"run_id": run_id, "status": status},
        )
        .mappings()
        .all()
    )
    as_of = rows[0]["ran_at"] if rows else None
    return envelope([dict(r) for r in rows], "meta.quality_run", as_of)


@router.get("/quality/runs", response_model=Envelope[list[QualityRun]])
def quality_runs(limit: int = Query(30, ge=1, le=500), conn: Connection = Depends(get_conn)):
    rows = (
        conn.execute(
            text(
                """
            select run_id, min(ran_at) as ran_at, count(*) as n_checks,
                   count(*) filter (where passed) as n_passed,
                   count(*) filter (where not passed and severity = 'error')   as n_error_failed,
                   count(*) filter (where not passed and severity = 'warning') as n_warning_failed
            from meta.quality_run
            group by run_id
            order by ran_at desc
            limit :limit
            """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )
    as_of = rows[0]["ran_at"] if rows else None
    return envelope([dict(r) for r in rows], "meta.quality_run", as_of)


@router.get("/layers", response_model=Envelope[list[LayerTable]])
def layers(conn: Connection = Depends(get_conn)):
    """Số dòng từng bảng ở mỗi tầng, theo lần profile mới nhất (quality.runner ghi)."""
    rows = (
        conn.execute(
            text(
                """
            select schema_name, table_name, row_count, profiled_at
            from meta.table_profile
            where run_id = (select run_id from meta.table_profile order by profiled_at desc limit 1)
            order by array_position(array['raw','staging','core','analytics','meta'], schema_name),
                     table_name
            """
            )
        )
        .mappings()
        .all()
    )
    as_of = rows[0]["profiled_at"] if rows else None
    return envelope([dict(r) for r in rows], "meta.table_profile", as_of)
