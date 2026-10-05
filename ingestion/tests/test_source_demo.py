from datetime import date
from itertools import islice

from ingestion.sources.source_demo import SourceDemo


def test_fetch_is_deterministic():
    a = list(SourceDemo().fetch(None))
    b = list(SourceDemo().fetch(None))
    assert a == b


def test_limit_is_prefix_of_full_run():
    # --limit phải cho đúng các bản ghi đầu của lần chạy đầy đủ, để hash khớp giữa các lô.
    full = list(SourceDemo().fetch(None))
    assert list(islice(SourceDemo().fetch(None), 100)) == full[:100]


def test_since_filters_by_event_date():
    since = date(2024, 1, 1)
    rows = list(SourceDemo().fetch(since))
    assert rows and all(r["event_date"] >= "2024-01-01" for r in rows)


def test_records_are_raw_text_with_expected_columns():
    rec = next(SourceDemo().fetch(None))
    assert set(rec) == set(SourceDemo.columns)
    assert all(isinstance(v, str) for v in rec.values())


def test_row_hash_stable_and_sensitive():
    c = SourceDemo()
    rec = {"record_id": "R1", "measure_value": "1.0"}
    assert c.row_hash(rec) == c.row_hash(dict(reversed(rec.items())))
    assert c.row_hash(rec) != c.row_hash({**rec, "measure_value": "1.00"})
