"""Connector openFDA: snapshot giới hạn của từ điển hoạt chất từ nhãn thuốc."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import date
from urllib.parse import urlencode

from ingestion import http_client
from ingestion.base import Connector, RawPage, SourceMeta

API_URL = "https://api.fda.gov/drug/label.json"
PAGE_SIZE = 1000
MAX_SKIP = 25_000
DISCLAIMER = (
    "Do not rely on openFDA to make decisions regarding medical care. "
    "Data should be assumed unvalidated."
)
TERMS_URL = "https://open.fda.gov/terms/"
LICENSE_URL = "https://open.fda.gov/license/"


class OpenFDA(Connector):
    name = "openfda"
    raw_table = "raw.openfda_substances"
    columns = ("spl_id", "substance_name", "rxcui")
    mock_format = "json"
    mock_page_size = PAGE_SIZE

    def describe(self) -> SourceMeta:
        return SourceMeta(
            description=(
                "Từ điển tên hoạt chất và RxCUI trích từ nhãn thuốc openFDA; "
                "chỉ dùng hỗ trợ chuẩn hóa văn bản, không phải dữ liệu vắc xin. "
                "Snapshot bị giới hạn bởi API skip tối đa 25.000."
            ),
            url=API_URL,
            license=f"Public domain (CC0); disclaimer: {LICENSE_URL}",
            update_frequency="Hàng tuần (meta.last_updated)",
            owner="Crawler B & Mock server",
        )

    def fetch_live(self, since: date | None) -> Iterator[RawPage]:
        # effective_time là ngày hiệu lực của nhãn, không phải ngày cập nhật nguồn.
        # Dùng since như bộ lọc nhãn khi được yêu cầu; mặc định lấy mọi nhãn có hoạt chất.
        search = "openfda.substance_name:*"
        if since is not None:
            search += f" AND effective_time:[{since.strftime('%Y%m%d')} TO 99999999]"

        skip = 0
        while skip <= MAX_SKIP:
            params = {"search": search, "limit": PAGE_SIZE, "skip": skip}
            response = http_client.get(API_URL, params=params)
            body = response.json()
            meta_results = body.get("meta", {}).get("results", {})
            page_total = int(meta_results.get("total", 0))
            content = response.content
            yield RawPage(
                url=str(response.url),
                content=content,
                content_type=response.headers.get("content-type", "application/json"),
                mode="live",
            )
            returned = len(body.get("results", []))
            if returned == 0 or skip + returned >= page_total or returned < PAGE_SIZE:
                break
            next_skip = skip + returned
            if next_skip > MAX_SKIP:
                break
            skip = next_skip

    def parse(self, page: RawPage) -> Iterator[dict]:
        body = json.loads(page.content)
        for label in body.get("results", []):
            openfda = label.get("openfda") or {}
            names = openfda.get("substance_name")
            if not names:
                continue
            spl_ids = openfda.get("spl_id") or []
            rxcuis = openfda.get("rxcui")
            record = {
                "spl_id": spl_ids[0] if spl_ids else None,
                "substance_name": json.dumps(names, ensure_ascii=False, separators=(",", ":")),
                "rxcui": (
                    json.dumps(rxcuis, ensure_ascii=False, separators=(",", ":"))
                    if rxcuis
                    else None
                ),
                # Loader stores this field in _payload. It also lets mock_server reconstruct
                # the original API result shape without inventing source data.
                "_source_payload": label,
            }
            yield record

    def render_api_page(self, records: list[dict], page: int, page_size: int, total: int) -> dict:
        results = [rec.get("_source_payload", rec) for rec in records]
        return {
            "meta": {
                "disclaimer": DISCLAIMER,
                "terms": TERMS_URL,
                "license": LICENSE_URL,
                "last_updated": "snapshot",
                "results": {
                    "skip": (page - 1) * page_size,
                    "limit": page_size,
                    "total": total,
                },
            },
            "results": results,
        }

    def row_hash(self, record: dict) -> str:
        spl_id = record.get("spl_id")
        if spl_id:
            return hashlib.md5(str(spl_id).encode("utf-8")).hexdigest()
        # Missing identifier: hash the complete original label, not NULL, so unrelated
        # records without spl_id do not collapse into one row.
        payload = record.get("_source_payload", record)
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(canonical.encode("utf-8")).hexdigest()
