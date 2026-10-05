"""Nạp dữ liệu cho mock_server từ CHÍNH các bản gốc mà lần chạy live đã lưu ở data/raw/.

Không sinh dữ liệu giả. Với mỗi nguồn: chọn snapshot live hoàn chỉnh mới nhất
(data/raw/<source>/<ngày>/<batch_id>/manifest.json có mode=live, complete=true), kiểm sha256
từng trang, rồi parse bằng đúng connector.parse() của nguồn đó. Vì cùng bản gốc + cùng parser,
bản ghi mock phát ra trùng khớp bản ghi lô live đã ghi vào raw.

    python -m mock_server.seed      # in ra snapshot mỗi nguồn sẽ được phát lại
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from common.db import REPO_ROOT
from ingestion import registry
from ingestion.base import RawPage


def raw_dir() -> Path:
    return Path(os.environ.get("MOCK_RAW_DIR", REPO_ROOT / "data" / "raw"))


@dataclass(frozen=True)
class Snapshot:
    source: str
    batch_id: str
    finished_at: str
    manifest: Path
    columns: list[str]
    records: list[dict]


_cache: dict[Path, tuple[float, Snapshot]] = {}


def sources() -> list[str]:
    return sorted(registry.SOURCES)


def latest_manifest(source: str) -> Path | None:
    best: tuple[str, Path] | None = None
    for path in (raw_dir() / source).glob("*/*/manifest.json"):
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("mode") == "live" and meta.get("complete"):
            if best is None or meta["finished_at"] > best[0]:
                best = (meta["finished_at"], path)
    return best[1] if best else None


def load(source: str) -> Snapshot | None:
    """Snapshot mới nhất của nguồn, cache theo file manifest (lô live mới -> tự nạp lại)."""
    if source not in registry.SOURCES:
        raise KeyError(source)
    path = latest_manifest(source)
    if path is None:
        return None
    mtime = path.stat().st_mtime
    cached = _cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]

    connector = registry.get(source)
    meta = json.loads(path.read_text(encoding="utf-8"))
    records: list[dict] = []
    for page in meta["pages"]:
        content = (path.parent / page["file"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != page["sha256"]:
            raise ValueError(f"{path.parent / page['file']} bị sửa sau khi lưu (sha256 lệch)")
        records.extend(connector.parse(RawPage(page["url"], content, page["content_type"], "live")))
    # Lô live chạy --limit chỉ dùng record_count bản ghi đầu; phát lại đúng phần đó.
    records = records[: meta["record_count"]]

    columns = list(connector.columns)
    for rec in records:
        columns.extend(k for k in rec if k not in columns)

    snap = Snapshot(source, meta["batch_id"], meta["finished_at"], path, columns, records)
    _cache[path] = (mtime, snap)
    return snap


def main() -> None:
    for source in sources():
        snap = load(source)
        if snap is None:
            print(f"{source:20s} chưa có snapshot live — chạy `make ingest SOURCE_MODE=live` trước")
        else:
            rel = snap.manifest.parent.relative_to(raw_dir())
            print(f"{source:20s} {len(snap.records):>7} bản ghi  từ {rel}  ({snap.finished_at})")


if __name__ == "__main__":
    main()
