"""Nguồn giả cho M1–M4: sinh sự kiện đo của 20 thực thể, có seed nên chạy lại ra đúng bản ghi cũ.

Dữ liệu cố tình bẩn để tầng transform và quality có việc làm (tỉ lệ xấp xỉ):
- 1%   record_id rỗng                        -> core bỏ dòng (cleaning_log #3)
- 0.5% bản ghi lặp lại cùng record_id         -> core giữ bản nạp sau (cleaning_log #4)
- 0.5% entity_code rỗng                       -> fct trỏ về thực thể unknown (key = -1)
- 2%   measure_value rỗng                     -> giữ NULL
- 10%  entity_code chữ thường / thừa khoảng trắng, category chữ thường -> staging chuẩn hóa
- 0.3% measure_value ngoại lai (x20)          -> check outlier cảnh báo

Thay bằng connector thật ở M5; khi đó xóa file này khỏi registry nhưng giữ làm ví dụ.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import date, timedelta

from ingestion.base import Connector, SourceMeta

N_RECORDS = 5000
SEED = 20261005
START = date(2020, 1, 1)
END = date(2025, 12, 31)
CATEGORIES = ["A", "B", "C", "D"]


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

    def __init__(self, n_records: int = N_RECORDS, seed: int = SEED):
        self.n_records = n_records
        self.seed = seed

    def describe(self) -> SourceMeta:
        return SourceMeta(
            description="Dữ liệu giả sinh ngẫu nhiên có seed, dùng dựng khung trước khi chốt topic.",
            url="local://ingestion/sources/source_demo.py",
            license="Nội bộ nhóm",
            update_frequency="on demand",
            owner="Data Acquisition",
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

    def fetch(self, since: date | None) -> Iterator[dict]:
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
