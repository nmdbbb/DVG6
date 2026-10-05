"""Map tên nguồn -> class connector. Thêm nguồn mới: import class và thêm một dòng vào SOURCES."""

from __future__ import annotations

from ingestion.base import Connector
from ingestion.sources.source_demo import SourceDemo

SOURCES: dict[str, type[Connector]] = {
    SourceDemo.name: SourceDemo,
}


def get(name: str) -> Connector:
    try:
        return SOURCES[name]()
    except KeyError:
        raise SystemExit(f"Không có nguồn '{name}'. Có: {', '.join(sorted(SOURCES))}") from None
