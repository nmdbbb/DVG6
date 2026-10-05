from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class Source(BaseModel):
    source_name: str
    description: str | None
    url: str | None
    license: str | None
    update_frequency: str | None
    owner: str | None
    batch_count: int
    total_rows: int
    last_batch_at: datetime | None
    last_status: str | None


class Batch(BaseModel):
    batch_id: UUID
    source_name: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    rows_fetched: int | None
    row_count: int | None
    bytes: int | None
    duration_seconds: float | None
    error_message: str | None


class QualityCheck(BaseModel):
    run_id: UUID
    check_name: str
    check_source: str
    severity: str
    passed: bool
    observed_value: Decimal | None
    threshold: str | None
    message: str | None
    ran_at: datetime


class QualityRun(BaseModel):
    run_id: UUID
    ran_at: datetime
    n_checks: int
    n_passed: int
    n_error_failed: int
    n_warning_failed: int


class LayerTable(BaseModel):
    schema_name: str
    table_name: str
    row_count: int
    profiled_at: datetime
