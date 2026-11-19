"""Ba connector VAERS chọn ZIP theo năm, đã tải tay và đăng ký checksum.

Live đọc ZIP local; mock dùng HTML của mock_server hiện có. Không cần Docker
để chạy preview: python -m ingestion.sources.vaers --limit 10
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import zipfile
from collections.abc import Iterator
from datetime import date
from itertools import islice
from pathlib import Path

from ingestion.base import Connector, RawPage, SourceMeta

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path(__file__).with_name("vaers_landing.json")


class VaersCSV(Connector):
    suffix: str
    mock_format = "html"

    def __init__(
        self,
        zip_path: Path | None = None,
        expected_sha256: str | None = None,
        year: int | None = None,
        encoding: str | None = None,
        page_size: int = 1000,
    ):
        manifest_path = Path(os.environ.get("VAERS_MANIFEST", DEFAULT_MANIFEST))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # Vẫn đọc được manifest một năm cũ; mặc định 2021 để không đổi phạm vi ngầm.
        datasets = manifest.get("datasets", [manifest])
        selected_year = year if year is not None else int(os.environ.get("VAERS_YEAR", "2021"))
        matches = [item for item in datasets if item["year"] == selected_year]
        if len(matches) != 1:
            raise ValueError(f"Expected one registered VAERS ZIP for year {selected_year}")
        manifest = matches[0]
        self.zip_path = Path(zip_path) if zip_path is not None else REPO_ROOT / manifest["path"]
        self.expected_sha256 = expected_sha256 or manifest["sha256"]
        self.year = year if year is not None else manifest["year"]
        self.encoding = encoding or manifest["encoding"]
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        self.page_size = page_size

    def describe(self) -> SourceMeta:
        return SourceMeta(
            description=f"VAERS {self.year}, CSV {self.suffix} nguyên trạng từ ZIP tải tay.",
            url="https://vaers.hhs.gov/data/datasets.html",
            license="U.S. government public data; VAERS Data Use Guide applies",
            update_frequency="Manual registered snapshot",
            owner="Source & Crawler A",
        )

    def fetch_live(self, since: date | None) -> Iterator[RawPage]:
        if since is not None:
            raise ValueError("VAERS reads a full registered ZIP; --since is not supported")
        # Kiểm checksum mỗi lần chạy, trước khi phát ra bất kỳ trang nào.
        with self.zip_path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != self.expected_sha256:
                raise ValueError("VAERS ZIP sha256 mismatch; register the new snapshot explicitly")
            stream.seek(0)
            with zipfile.ZipFile(stream) as archive:
                expected = f"{self.year}VAERS{self.suffix}.csv"
                matches = [
                    info
                    for info in archive.infolist()
                    if not info.is_dir()
                    and Path(info.filename).name.casefold() == expected.casefold()
                ]
                if len(matches) != 1:
                    raise ValueError(f"Expected exactly one {expected}; found {len(matches)}")
                with archive.open(matches[0]) as member:
                    # Reader chỉ xác định ranh giới bản ghi (CSV có thể chứa xuống dòng).
                    # Trang phát ra giữ nguyên bytes nguồn; loader lưu trước parse().
                    captured: list[bytes] = []

                    def lines():
                        for line in member:
                            captured.append(line)
                            yield line.decode(self.encoding)

                    reader = csv.reader(lines(), strict=True)
                    header = next(reader, None)
                    if header != list(self.columns):
                        raise ValueError(f"Unexpected CSV header in {expected}")
                    header_bytes = b"".join(captured)
                    captured.clear()
                    count = 0
                    chunks: list[bytes] = [header_bytes]
                    page = 1
                    for _ in reader:
                        chunks.extend(captured)
                        captured.clear()
                        count += 1
                        if count == self.page_size:
                            yield self._page(expected, page, b"".join(chunks))
                            chunks, count = [header_bytes], 0
                            page += 1
                    if count:
                        yield self._page(expected, page, b"".join(chunks))
                    elif page == 1:
                        # CSV chỉ có header vẫn phải lưu được snapshot gốc.
                        yield self._page(expected, page, header_bytes)

    def _page(self, member: str, number: int, content: bytes) -> RawPage:
        return RawPage(
            url=f"{self.zip_path.resolve().as_uri()}!/{member}?page={number}",
            content=content,
            content_type=f"text/csv; charset={self.encoding}",
            mode="live",
        )

    def parse(self, page: RawPage) -> Iterator[dict]:
        # Dùng charset ghi trong snapshot để phát lại đúng cả khi cấu hình thay đổi.
        encoding = page.content_type.partition("charset=")[2].strip() or self.encoding
        with io.TextIOWrapper(io.BytesIO(page.content), encoding=encoding, newline="") as text:
            reader = csv.reader(text, strict=True)
            if next(reader, None) != list(self.columns):
                raise ValueError(f"Unexpected CSV header for {self.name}")
            for line_number, values in enumerate(reader, start=2):
                if len(values) != len(self.columns):
                    raise ValueError(f"Wrong column count for {self.name}, record {line_number}")
                yield dict(zip(self.columns, values, strict=True))


class VaersData(VaersCSV):
    name = "vaers_data"
    raw_table = "raw.vaers_data"
    suffix = "DATA"
    columns = (
        "VAERS_ID",
        "RECVDATE",
        "STATE",
        "AGE_YRS",
        "CAGE_YR",
        "CAGE_MO",
        "SEX",
        "RPT_DATE",
        "SYMPTOM_TEXT",
        "DIED",
        "DATEDIED",
        "L_THREAT",
        "ER_VISIT",
        "HOSPITAL",
        "HOSPDAYS",
        "X_STAY",
        "DISABLE",
        "RECOVD",
        "VAX_DATE",
        "ONSET_DATE",
        "NUMDAYS",
        "LAB_DATA",
        "V_ADMINBY",
        "V_FUNDBY",
        "OTHER_MEDS",
        "CUR_ILL",
        "HISTORY",
        "PRIOR_VAX",
        "SPLTTYPE",
        "FORM_VERS",
        "TODAYS_DATE",
        "BIRTH_DEFECT",
        "OFC_VISIT",
        "ER_ED_VISIT",
        "ALLERGIES",
        "ORDER",
    )


class VaersSymptoms(VaersCSV):
    name = "vaers_symptoms"
    raw_table = "raw.vaers_symptoms"
    suffix = "SYMPTOMS"
    columns = (
        "VAERS_ID",
        "SYMPTOM1",
        "SYMPTOMVERSION1",
        "SYMPTOM2",
        "SYMPTOMVERSION2",
        "SYMPTOM3",
        "SYMPTOMVERSION3",
        "SYMPTOM4",
        "SYMPTOMVERSION4",
        "SYMPTOM5",
        "SYMPTOMVERSION5",
        "ORDER",
    )


class VaersVax(VaersCSV):
    name = "vaers_vax"
    raw_table = "raw.vaers_vax"
    suffix = "VAX"
    columns = (
        "VAERS_ID",
        "VAX_TYPE",
        "VAX_MANU",
        "VAX_LOT",
        "VAX_DOSE_SERIES",
        "VAX_ROUTE",
        "VAX_SITE",
        "VAX_NAME",
        "ORDER",
    )


VAERS_CONNECTORS = (VaersData, VaersSymptoms, VaersVax)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview VAERS locally without database writes")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--year", type=int, help="Registered year; default VAERS_YEAR or 2021")
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error("--limit must be positive")
    for cls in VAERS_CONNECTORS:
        connector = cls(year=args.year)
        rows = (row for page in connector.fetch_live(None) for row in connector.parse(page))
        count = sum(1 for _ in islice(rows, args.limit))
        print(
            f"{connector.name} year={connector.year}: checksum OK, "
            f"parsed {count} records -> {connector.raw_table}"
        )


if __name__ == "__main__":
    main()
