import csv
import hashlib
import html
import io
import json
import re
import zipfile
from datetime import date
from pathlib import Path

import pytest

from ingestion import registry
from ingestion.base import RawPage
from ingestion.sources.vaers import VAERS_CONNECTORS, VaersData


def make_zip(tmp_path, cls=VaersData, *, header=None, rows=None):
    text = io.StringIO(newline="")
    writer = csv.writer(text)
    writer.writerow(header if header is not None else cls.columns)
    if rows is None:
        rows = [[" 1 ", 'rash, "pain"\r\nnext line; café', *([""] * (len(cls.columns) - 2))]] * 3
    writer.writerows(rows)
    content = text.getvalue().encode("cp1252")
    path = tmp_path / "vaers.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"2021VAERS{cls.suffix}.csv", content)
    connector = cls(path, hashlib.sha256(path.read_bytes()).hexdigest(), page_size=2)
    return connector, content


@pytest.mark.parametrize("cls", VAERS_CONNECTORS)
def test_raw_pages_preserve_bytes_and_values(tmp_path, cls):
    connector, content = make_zip(tmp_path, cls)
    pages = list(connector.fetch_live(None))
    assert len(pages) == 2
    header = content.split(b"\r\n", 1)[0] + b"\r\n"
    assert pages[0].content + pages[1].content[len(header) :] == content
    records = [record for page in pages for record in connector.parse(page)]
    assert len(records) == 3
    assert records[0][cls.columns[0]] == " 1 "
    assert records[0][cls.columns[1]] == 'rash, "pain"\r\nnext line; café'
    assert records[0][cls.columns[-1]] == ""
    assert records[0] == records[1] == records[2]
    assert connector.row_hash(records[0]) == connector.row_hash(records[-1])


def test_checksum_mismatch_stops_before_first_page(tmp_path):
    connector, _ = make_zip(tmp_path)
    connector.zip_path.write_bytes(connector.zip_path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="sha256"):
        next(connector.fetch_live(None))


def test_missing_member_and_wrong_header(tmp_path):
    connector, _ = make_zip(tmp_path)
    connector.suffix = "VAX"
    with pytest.raises(ValueError, match="Expected exactly one"):
        next(connector.fetch_live(None))
    connector, _ = make_zip(tmp_path, header=["WRONG"])
    with pytest.raises(ValueError, match="header"):
        next(connector.fetch_live(None))


def test_wrong_column_count_is_not_silently_truncated(tmp_path):
    connector, _ = make_zip(tmp_path, rows=[["1", "too few"]])
    page = next(connector.fetch_live(None))
    with pytest.raises(ValueError, match="column count"):
        list(connector.parse(page))


def test_no_since_filtering(tmp_path):
    connector, _ = make_zip(tmp_path)
    with pytest.raises(ValueError, match="since"):
        next(connector.fetch_live(date(2021, 1, 1)))


def test_mock_html_keeps_hash_without_local_zip(tmp_path):
    connector, _ = make_zip(tmp_path)
    record = next(connector.parse(next(connector.fetch_live(None))))
    connector.zip_path.unlink()
    markup = '<table id="records"><tr>'
    markup += "".join(f"<th>{html.escape(c)}</th>" for c in connector.columns)
    markup += "</tr><tr>"
    markup += "".join(f"<td>{html.escape(record[c])}</td>" for c in connector.columns)
    markup += "</tr></table>"
    page = RawPage("http://mock/vaers_data", markup.encode(), "text/html", "mock")
    replay = list(connector.records(page))
    assert replay == [record]
    assert connector.row_hash(replay[0]) == connector.row_hash(record)


@pytest.mark.parametrize("cls", VAERS_CONNECTORS)
def test_registered_columns_match_migration(cls):
    sql_path = Path(__file__).resolve().parents[2] / "db/migrations/006_vaers_raw_tables.sql"
    sql = sql_path.read_text(encoding="utf-8")
    table = re.search(r"create table " + re.escape(cls.raw_table) + r" \((.*?)\n\);", sql, re.S)
    assert table is not None
    assert tuple(re.findall(r'^    "([^"]+)" text', table[1], re.M)) == cls.columns
    assert isinstance(registry.get(cls.name), cls)


def test_empty_csv_has_header_snapshot(tmp_path):
    connector, content = make_zip(tmp_path, rows=[])
    pages = list(connector.fetch_live(None))
    assert len(pages) == 1 and pages[0].content == content
    assert list(connector.parse(pages[0])) == []


def test_year_selection_uses_matching_path_and_checksum(tmp_path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    datasets = [
        {"year": year, "path": f"{year}.zip", "sha256": str(year), "encoding": "cp1252"}
        for year in (2021, 2022, 2026)
    ]
    manifest.write_text(json.dumps({"datasets": datasets}), encoding="utf-8")
    monkeypatch.setenv("VAERS_MANIFEST", str(manifest))
    monkeypatch.delenv("VAERS_YEAR", raising=False)
    assert VaersData().year == 2021
    monkeypatch.setenv("VAERS_YEAR", "2022")
    connector = VaersData()
    assert connector.year == 2022
    assert connector.zip_path.name == "2022.zip"
    assert connector.expected_sha256 == "2022"
    assert VaersData(year=2026).year == 2026
    with pytest.raises(ValueError, match="registered"):
        VaersData(year=2020)


def test_legacy_manifest_still_supported(tmp_path, monkeypatch):
    manifest = tmp_path / "legacy.json"
    manifest.write_text(
        json.dumps({"year": 2021, "path": "old.zip", "sha256": "abc", "encoding": "cp1252"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("VAERS_MANIFEST", str(manifest))
    monkeypatch.delenv("VAERS_YEAR", raising=False)
    assert VaersData().zip_path.name == "old.zip"
