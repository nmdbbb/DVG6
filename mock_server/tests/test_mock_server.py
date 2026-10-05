"""Mock server phát lại đúng bản ghi của snapshot live, qua cả JSON lẫn HTML."""

import hashlib
import json
import time

import pytest
from fastapi.testclient import TestClient

from ingestion.base import RawPage, parse_mock_html
from ingestion.sources.source_demo import SourceDemo
from mock_server import app as mock_app
from mock_server import seed

N = 130


def _write_snapshot(root, records_used=N, n_records=N, finished="2026-01-01T00:00:00+00:00"):
    c = SourceDemo(n_records=n_records)
    folder = root / "source_demo" / "2026-01-01" / f"batch-{records_used}-{finished[:4]}"
    folder.mkdir(parents=True)
    pages = []
    for i, page in enumerate(c.fetch(None, "live"), 1):
        name = f"page_{i:05d}{page.suffix}"
        (folder / name).write_bytes(page.content)
        pages.append(
            {
                "file": name,
                "url": page.url,
                "content_type": page.content_type,
                "bytes": len(page.content),
                "sha256": hashlib.sha256(page.content).hexdigest(),
            }
        )
    manifest = {
        "source": "source_demo",
        "batch_id": folder.name,
        "mode": "live",
        "params": {},
        "complete": True,
        "finished_at": finished,
        "record_count": records_used,
        "pages": pages,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return list(c.generate(None))[:records_used]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_RAW_DIR", str(tmp_path))
    monkeypatch.setattr(mock_app.settings, "latency_min_ms", 0)
    monkeypatch.setattr(mock_app.settings, "latency_max_ms", 0)
    monkeypatch.setattr(mock_app.settings, "rate_limit_per_min", 0)
    seed._cache.clear()
    mock_app.limiter.reset()
    return TestClient(mock_app.app)


def _crawl(client, url):
    pages = []
    while url:
        r = client.get(url)
        assert r.status_code == 200, r.text
        pages.append(r)
        url = r.links.get("next", {}).get("url")
    return pages


def test_no_snapshot_is_503(client):
    assert client.get("/api/source_demo").status_code == 503
    assert client.get("/health").json()["snapshots"]["source_demo"] is None


def test_unknown_source_is_404(client, tmp_path):
    _write_snapshot(tmp_path)
    assert client.get("/api/khong_co").status_code == 404


def test_json_replays_live_records_in_api_shape(client, tmp_path):
    expected = _write_snapshot(tmp_path)
    c = SourceDemo()
    pages = _crawl(client, "/api/source_demo?page=1&page_size=50")
    assert len(pages) == 3
    assert set(pages[0].json()) == {"count", "page", "page_size", "results"}  # hình dạng API thật
    got = [
        rec
        for r in pages
        for rec in c.parse(RawPage(str(r.url), r.content, r.headers["content-type"], "mock"))
    ]
    assert got == expected
    assert [c.row_hash(x) for x in got] == [c.row_hash(x) for x in expected]


def test_html_pages_20_rows_with_next_link(client, tmp_path):
    expected = _write_snapshot(tmp_path)
    pages = _crawl(client, "/source_demo?page=1")
    assert len(pages) == -(-N // 20)
    assert '<a rel="next"' in pages[0].text and '<a rel="next"' not in pages[-1].text
    rows = [list(parse_mock_html(r.content)) for r in pages]
    assert all(len(r) == 20 for r in rows[:-1])
    assert [rec for page in rows for rec in page] == expected  # giữ cả khoảng trắng, chuỗi rỗng


def test_replays_only_records_the_live_batch_used(client, tmp_path):
    expected = _write_snapshot(tmp_path, records_used=37)
    body = client.get("/api/source_demo?page_size=1000").json()
    assert body["count"] == 37 and body["results"] == expected


def test_serves_newest_complete_snapshot(client, tmp_path):
    _write_snapshot(tmp_path, records_used=10, finished="2026-01-01T00:00:00+00:00")
    _write_snapshot(tmp_path, records_used=20, finished="2027-01-01T00:00:00+00:00")
    assert client.get("/api/source_demo").json()["count"] == 20


def test_rate_limit_429_with_retry_after_and_health_exempt(client, tmp_path, monkeypatch):
    _write_snapshot(tmp_path)
    monkeypatch.setattr(mock_app.settings, "rate_limit_per_min", 3)
    codes = [client.get("/api/source_demo").status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    r = client.get("/api/source_demo")
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1
    assert client.get("/health").status_code == 200


def test_latency_applied(client, tmp_path, monkeypatch):
    _write_snapshot(tmp_path)
    monkeypatch.setattr(mock_app.settings, "latency_min_ms", 60)
    monkeypatch.setattr(mock_app.settings, "latency_max_ms", 80)
    t = time.perf_counter()
    client.get("/api/source_demo")
    assert time.perf_counter() - t >= 0.06


def test_tampered_page_is_rejected(client, tmp_path):
    _write_snapshot(tmp_path)
    page = next((tmp_path / "source_demo").rglob("page_00001.json"))
    page.write_bytes(page.read_bytes().replace(b"R0000", b"X0000", 1))
    seed._cache.clear()
    with pytest.raises(ValueError, match="sha256"):
        client.get("/api/source_demo")
