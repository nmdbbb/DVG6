"""Hợp đồng chung cho mọi connector. Thêm nguồn mới = thêm một class trong sources/ + đăng ký
trong registry.py + một migration tạo bảng raw. Không sửa loader hay CLI.

Quy tắc (docs/data_contract.md):
- Không làm sạch trong connector: không đổi tên cột, không ép kiểu, không lọc dòng.
- fetch() chạy lại cùng tham số phải cho cùng bản ghi (idempotent).
- Bản gốc được loader lưu xuống data/raw/<source>/<ngày>/ trước khi ghi database.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SourceMeta:
    description: str
    url: str
    license: str
    update_frequency: str
    owner: str


class Connector(ABC):
    name: str  # khớp meta.source.source_name
    raw_table: str  # ví dụ "raw.source_demo_records"
    columns: tuple[str, ...]  # cột nghiệp vụ của bảng raw, đúng thứ tự trong migration

    @abstractmethod
    def fetch(self, since: date | None) -> Iterator[dict]:
        """Trả về từng bản ghi thô. Không làm sạch, không ép kiểu."""

    def row_hash(self, record: dict) -> str:
        """Khóa định danh bản ghi để khử trùng lặp giữa các lô.

        Mặc định: md5 của toàn bộ bản ghi dạng JSON sắp khóa. Override nếu nguồn có khóa ổn định.
        """
        canonical = json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(canonical.encode("utf-8")).hexdigest()

    @abstractmethod
    def describe(self) -> SourceMeta:
        """url, license, tần suất cập nhật, chủ sở hữu — ghi vào meta.source."""
