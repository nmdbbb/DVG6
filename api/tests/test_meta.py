from api.tests.conftest import assert_envelope


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["schema_version"] is not None


def test_sources_lists_demo_source(client):
    data = assert_envelope(client.get("/meta/sources").json())
    names = {s["source_name"] for s in data}
    assert "source_demo" in names


def test_batches_filter_by_source_and_status(client):
    data = assert_envelope(
        client.get("/meta/batches", params={"source": "source_demo", "status": "success"}).json()
    )
    assert data, "Cần ít nhất một lô success — chạy make ingest trước"
    assert all(b["source_name"] == "source_demo" and b["status"] == "success" for b in data)


def test_batches_filter_by_mode(client):
    data = assert_envelope(client.get("/meta/batches", params={"mode": "live"}).json())
    assert data and all(b["source_mode"] == "live" for b in data)


def test_batches_rejects_bad_status(client):
    assert client.get("/meta/batches", params={"status": "nope"}).status_code == 422


def test_quality_latest_run(client):
    data = assert_envelope(client.get("/meta/quality").json())
    assert data, "Cần ít nhất một lần chạy quality — chạy make quality trước"
    assert len({c["run_id"] for c in data}) == 1


def test_quality_failed_filter(client):
    data = assert_envelope(client.get("/meta/quality", params={"status": "failed"}).json())
    assert all(not c["passed"] for c in data)


def test_quality_runs_summary(client):
    data = assert_envelope(client.get("/meta/quality/runs").json())
    assert data and all(r["n_checks"] >= r["n_passed"] for r in data)


def test_layers_cover_all_tiers(client):
    data = assert_envelope(client.get("/meta/layers").json())
    assert {"raw", "staging", "core", "analytics"} <= {t["schema_name"] for t in data}
