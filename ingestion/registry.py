"""Map tên nguồn -> class connector. Thêm nguồn mới: import class và thêm một dòng vào SOURCES."""

from __future__ import annotations

from ingestion.base import Connector
from ingestion.sources.source_demo import SourceDemo
from ingestion.sources.vaers import VaersData, VaersSymptoms, VaersVax

SOURCES: dict[str, type[Connector]] = {
    SourceDemo.name: SourceDemo,
    VaersData.name: VaersData,
    VaersSymptoms.name: VaersSymptoms,
    VaersVax.name: VaersVax,
}


def get(name: str) -> Connector:
    try:
        return SOURCES[name]()
    except KeyError:
        raise SystemExit(f"Không có nguồn '{name}'. Có: {', '.join(sorted(SOURCES))}") from None
