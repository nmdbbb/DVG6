from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    as_of: datetime | None = None
    row_count: int
    source: str


class Envelope(BaseModel, Generic[T]):
    """Mọi response bọc trong {data, meta}."""

    data: T
    meta: Meta


def envelope(data, source: str, as_of: datetime | None = None) -> dict:
    count = len(data) if isinstance(data, list) else 1
    return {"data": data, "meta": {"as_of": as_of, "row_count": count, "source": source}}
