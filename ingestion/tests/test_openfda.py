import hashlib
import json
from types import SimpleNamespace

from ingestion.base import RawPage
from ingestion.sources.openfda import API_URL, OpenFDA


def _label(spl_id="id-1", names=None, rxcui=None):
    openfda = {"substance_name": names or ["POVIDONE-IODINE"]}
    if spl_id is not None:
        openfda["spl_id"] = [spl_id]
    if rxcui is not None:
        openfda["rxcui"] = rxcui
    return {"id": spl_id or "label-without-spl", "openfda": openfda}


def _page(labels, mode="live"):
    body = {
        "meta": {"results": {"skip": 0, "limit": len(labels), "total": len(labels)}},
        "results": labels,
    }
    return RawPage("https://example.test", json.dumps(body).encode(), "application/json", mode)


def test_parse_keeps_arrays_and_source_payload():
    connector = OpenFDA()
    label = _label(names=["A", "B"], rxcui=["1", "2"])
    record = next(connector.parse(_page([label])))
    assert record["spl_id"] == "id-1"
    assert json.loads(record["substance_name"]) == ["A", "B"]
    assert json.loads(record["rxcui"]) == ["1", "2"]
    assert record["_source_payload"] == label


def test_parse_skips_labels_without_substance_name():
    connector = OpenFDA()
    assert list(connector.parse(_page([{"openfda": {"spl_id": ["x"]}}]))) == []


def test_missing_rxcui_is_null_and_missing_spl_id_has_stable_hash():
    connector = OpenFDA()
    a = next(connector.parse(_page([_label(spl_id=None, rxcui=None)])))
    b = next(connector.parse(_page([_label(spl_id=None, names=["OTHER"], rxcui=None)])))
    assert a["rxcui"] is None
    assert connector.row_hash(a) == connector.row_hash(a)
    assert connector.row_hash(a) != connector.row_hash(b)


def test_hash_uses_spl_id():
    connector = OpenFDA()
    a = {"spl_id": "stable-id", "substance_name": '["A"]'}
    b = {"spl_id": "stable-id", "substance_name": '["B"]'}
    assert connector.row_hash(a) == connector.row_hash(b) == hashlib.md5(b"stable-id").hexdigest()


def test_mock_render_preserves_original_api_results():
    connector = OpenFDA()
    label = _label(rxcui=["1"])
    record = next(connector.parse(_page([label])))
    body = connector.render_api_page([record], 1, 1000, 1)
    assert set(body) == {"meta", "results"}
    assert body["results"] == [label]
    assert body["meta"]["results"] == {"skip": 0, "limit": 1000, "total": 1}
    reparsed = list(
        connector.parse(RawPage("mock", json.dumps(body).encode(), "application/json", "mock"))
    )
    assert connector.row_hash(reparsed[0]) == connector.row_hash(record)


def test_fetch_live_respects_max_skip(monkeypatch):
    connector = OpenFDA()
    calls = []

    def fake_get(url, params):
        calls.append(params.copy())
        labels = [_label(f"id-{params['skip'] + i}") for i in range(params["limit"])]
        body = {"meta": {"results": {"total": 100000}}, "results": labels}
        return SimpleNamespace(
            json=lambda: body,
            content=json.dumps(body).encode(),
            headers={"content-type": "application/json"},
            url=f"{url}?{params['skip']}",
        )

    monkeypatch.setattr("ingestion.sources.openfda.http_client.get", fake_get)
    pages = list(connector.fetch_live(None))
    assert len(pages) == 26
    assert calls[0]["skip"] == 0
    assert calls[-1]["skip"] == 25000
    assert all(call["skip"] <= 25000 for call in calls)
    assert all(call["limit"] == 1000 for call in calls)
    assert all(call["search"] == "openfda.substance_name:*" for call in calls)
    assert API_URL in pages[0].url or pages[0].url.startswith(API_URL)
