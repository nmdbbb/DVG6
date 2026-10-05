from datetime import date
from itertools import islice

import pytest

from ingestion.sources.source_demo import API_PAGE_SIZE, SourceDemo


def test_fetch_is_deterministic():
    a = list(SourceDemo().generate(None))
    b = list(SourceDemo().generate(None))
    assert a == b


def test_limit_is_prefix_of_full_run():
    # --limit phải cho đúng các bản ghi đầu của lần chạy đầy đủ, để hash khớp giữa các lô.
    full = list(SourceDemo().generate(None))
    assert list(islice(SourceDemo().generate(None), 100)) == full[:100]


def test_since_filters_by_event_date():
    since = date(2024, 1, 1)
    rows = list(SourceDemo().generate(since))
    assert rows and all(r["event_date"] >= "2024-01-01" for r in rows)


def test_records_are_raw_text_with_expected_columns():
    rec = next(SourceDemo().generate(None))
    assert set(rec) == set(SourceDemo.columns)
    assert all(isinstance(v, str) for v in rec.values())


def test_row_hash_stable_and_sensitive():
    c = SourceDemo()
    rec = {"record_id": "R1", "measure_value": "1.0"}
    assert c.row_hash(rec) == c.row_hash(dict(reversed(rec.items())))
    assert c.row_hash(rec) != c.row_hash({**rec, "measure_value": "1.00"})


def test_live_pages_round_trip_through_parse():
    c = SourceDemo(n_records=1234)
    pages = list(c.fetch(None, "live"))
    assert len(pages) == -(-1234 // API_PAGE_SIZE)
    assert all(p.mode == "live" and p.suffix == ".json" for p in pages)
    parsed = [rec for p in pages for rec in c.records(p)]
    assert parsed == list(c.generate(None))


def test_mock_mode_rejects_since():
    with pytest.raises(ValueError, match="since"):
        next(SourceDemo().fetch(date(2024, 1, 1), "mock"))
