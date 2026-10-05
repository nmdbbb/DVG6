"""Nguồn giả cho M1–M4: sinh sự kiện đo của 20 thực thể, có seed nên chạy lại ra đúng bản ghi cũ.

Dữ liệu cố tình bẩn để tầng transform và quality có việc làm (tỉ lệ xấp xỉ):
- 1%   record_id rỗng                        -> core bỏ dòng (cleaning_log #3)
- 0.5% bản ghi lặp lại cùng record_id         -> core giữ bản nạp sau (cleaning_log #4)
- 0.5% entity_code rỗng                       -> fct trỏ về thực thể unknown (key = -1)
- 2%   measure_value rỗng                     -> giữ NULL
- 10%  entity_code chữ thường / thừa khoảng trắng, category chữ thường -> staging chuẩn hóa
- 0.3% measure_value ngoại lai (x20)          -> check outlier cảnh báo

Đường live giả lập một API JSON phân trang (500 bản ghi/trang, chạy trong process, không có mạng)
để minh họa đủ vòng live -> lưu bản gốc -> mock_server phát lại. Connector thật ở M5 viết
fetch_live() bằng http_client.get() tới URL thật.

Thay bằng connector thật ở M5; khi đó xóa file này khỏi registry nhưng giữ làm ví dụ.
"""

from __future__ import annotations

import json
import random
from collections.abc import Iterator
from datetime import date, timedelta

from ingestion.base import Connector, RawPage, SourceMeta

N_RECORDS = 5000
SEED = 20261005
START = date(2020, 1, 1)
END = date(2025, 12, 31)
CATEGORIES = ["A", "B", "C", "D"]
API_PAGE_SIZE = 500


class SourceDemo(Connector):
    name = "source_demo"
    raw_table = "raw.source_demo_records"
    columns = (
        "record_id",
        "entity_code",
        "entity_name",
        "category",
        "event_date",
        "measure_value",
    )
    mock_format = "json"
    mock_page_size = API_PAGE_SIZE

    def __init__(self, n_records: int = N_RECORDS, seed: int = SEED):
        self.n_records = n_records
        self.seed = seed

    def describe(self) -> SourceMeta:
        return SourceMeta(
            description="Dữ liệu giả sinh ngẫu nhiên có seed, dùng dựng khung trước khi chốt topic.",
            url="local://ingestion/sources/source_demo.py",
            license="Nội bộ nhóm",
            update_frequency="on demand",
            owner="Source & Crawler A",
        )

    def _entities(self, rng: random.Random) -> list[dict]:
        return [
            {
                "code": f"E{i:03d}",
                "name": f"Entity {i:02d}",
                "category": CATEGORIES[(i - 1) % len(CATEGORIES)],
                "base": rng.uniform(20, 200),
            }
            for i in range(1, 21)
        ]

    # ---------------------------------------------------------------- "API" giả lập

    def render_api_page(self, records: list[dict], page: int, page_size: int, total: int) -> dict:
        # Hình dạng response của "API" source_demo; mock_server phát lại đúng hình dạng này.
        return {"count": total, "page": page, "page_size": page_size, "results": records}

    def fetch_live(self, since: date | None) -> Iterator[RawPage]:
        records = list(self.generate(since))
        n_pages = max(1, -(-len(records) // API_PAGE_SIZE))
        for page in range(1, n_pages + 1):
            chunk = records[(page - 1) * API_PAGE_SIZE : page * API_PAGE_SIZE]
            body = self.render_api_page(chunk, page, API_PAGE_SIZE, len(records))
            query = f"page={page}&page_size={API_PAGE_SIZE}" + (f"&since={since}" if since else "")
            yield RawPage(
                url=f"demo://api/records?{query}",
                content=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                content_type="application/json",
                mode="live",
            )

    def parse(self, page: RawPage) -> Iterator[dict]:
        yield from json.loads(page.content)["results"]

    # ---------------------------------------------------------------- bộ sinh dữ liệu

    def generate(self, since: date | None) -> Iterator[dict]:
        rng = random.Random(self.seed)
        entities = self._entities(rng)
        span = (END - START).days
        previous: dict | None = None

        for i in range(1, self.n_records + 1):
            # 0.5%: lặp lại record_id của bản ghi trước, khác khoảng trắng -> khác hash, trùng khóa
            if previous is not None and rng.random() < 0.005:
                dup = dict(previous)
                dup["entity_name"] = f" {dup['entity_name']} "
                record = dup
            else:
                ent = rng.choice(entities)
                event_date = START + timedelta(days=rng.randrange(span + 1))
                measure = rng.lognormvariate(0, 0.35) * ent["base"]
                if rng.random() < 0.003:
                    measure *= 20

                code = ent["code"]
                category = ent["category"]
                if rng.random() < 0.10:
                    code = f"  {code.lower()} "
                    category = category.lower()

                record = {
                    "record_id": "" if rng.random() < 0.01 else f"R{i:06d}",
                    "entity_code": "" if rng.random() < 0.005 else code,
                    "entity_name": ent["name"],
                    "category": category,
                    "event_date": event_date.isoformat(),
                    "measure_value": "" if rng.random() < 0.02 else f"{measure:.2f}",
                }
            previous = record

            if since is not None and record["event_date"] < since.isoformat():
                continue
            yield record
