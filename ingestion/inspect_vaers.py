"""Kiểm tra ZIP VAERS, chỉ đọc file, không giải nén ra đĩa hay kết nối database.

Chạy từ thư mục repo:
    python -m ingestion.inspect_vaers data/landing/vaers/2026-10-15/2021VAERSData.zip
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path


def inspect_zip(path: Path, year: int = 2021) -> dict:
    """Kiểm CRC toàn bộ ZIP, đọc header CSV và tính SHA-256 theo khối."""
    if not path.is_file():
        raise ValueError(f"File does not exist: {path}")

    files = []
    with zipfile.ZipFile(path) as archive:
        # Dùng đúng tên file để không nhầm bộ dữ liệu của năm khác.
        for suffix in ("DATA", "SYMPTOMS", "VAX"):
            expected = f"{year}VAERS{suffix}.csv"
            matches = [
                info
                for info in archive.infolist()
                if not info.is_dir() and Path(info.filename).name.casefold() == expected.casefold()
            ]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one {expected}; found {len(matches)}")
            info = matches[0]
            with archive.open(info) as stream:
                # Header VAERS là tên cột ASCII; hỗ trợ cả BOM UTF-8.
                with io.TextIOWrapper(stream, encoding="utf-8-sig", newline="") as text:
                    columns = next(csv.reader(text), [])
            if not columns or any(not column.strip() for column in columns):
                raise ValueError(f"Empty CSV or blank column name: {info.filename}")
            if "VAERS_ID" not in columns or len(set(columns)) != len(columns):
                raise ValueError(f"Missing VAERS_ID or duplicate column names: {info.filename}")
            files.append(
                {
                    "name": info.filename,
                    "uncompressed_bytes": info.file_size,
                    "column_count": len(columns),
                    "columns": columns,
                }
            )

        # Đọc toàn bộ nội dung để phát hiện dữ liệu hỏng, không chỉ kiểm tên/header.
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"ZIP CRC check failed: {bad_member}")

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return {
        "status": "ok",
        "path": str(path.resolve()),
        "year": year,
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "zip_crc": "ok",
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Path to the original VAERS ZIP")
    parser.add_argument("--year", type=int, default=2021, help="Expected year (default: 2021)")
    args = parser.parse_args()
    try:
        result = inspect_zip(args.path, args.year)
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, csv.Error, EOFError) as exc:
        print(f"VAERS ZIP check failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
