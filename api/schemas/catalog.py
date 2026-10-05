from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class Table(BaseModel):
    schema_name: str
    table_name: str
    kind: str
    comment: str | None
    column_count: int
    row_count: int | None
    profiled_at: datetime | None


class Column(BaseModel):
    position: int
    column_name: str
    data_type: str
    nullable: bool
    comment: str | None
    null_count: int | None
    null_rate: Decimal | None
