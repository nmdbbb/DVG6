"""Hợp đồng chung cho mọi connector. Thêm nguồn mới = thêm một class trong sources/ + đăng ký
trong registry.py + một migration tạo bảng raw. Không sửa loader hay CLI.

Hai đường lấy dữ liệu (SOURCE_MODE / --endpoint):
- live (mặc định, đường chính): fetch_live() gọi nguồn thật. Loader lưu từng trang gốc xuống
  data/raw/<source>/<ngày>/<batch_id>/ TRƯỚC khi parse.
- mock (đường dự phòng): crawl mock_server, nơi phát lại đúng các trang gốc đã lưu của lần live
  gần nhất. Dùng khi nguồn thật chậm, bị chặn, đổi cấu trúc, hoặc cần chạy lại pipeline nhanh.
Hai đường phải cho ra cùng bản ghi, nên cùng _row_hash trong raw (scripts/compare_batches.py).

Quy tắc (docs/data_contract.md):
- Không làm sạch trong connector: không đổi tên cột, không ép kiểu, không lọc dòng.
- fetch_live() chạy lại cùng tham số phải cho cùng bản ghi (idempotent).
"""

from __future__ import annotations

import hashlib
import json
import os
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from typing import Literal

from ingestion import http_client

SourceMode = Literal["live", "mock"]
SOURCE_MODES: tuple[str, ...] = ("live", "mock")


@dataclass(frozen=True)
class SourceMeta:
    description: str
    url: str
    license: str
    update_frequency: str
    owner: str


@dataclass(frozen=True)
class RawPage:
    """Một phản hồi gốc từ nguồn (một trang API hoặc một trang HTML), chưa parse."""

    url: str
    content: bytes
    content_type: str
    mode: SourceMode

    @property
    def suffix(self) -> str:
        if "json" in self.content_type:
            return ".json"
        if "html" in self.content_type:
            return ".html"
        return ".bin"


class Connector(ABC):
    name: str  # khớp meta.source.source_name
    raw_table: str  # ví dụ "raw.source_demo_records"
    columns: tuple[str, ...]  # cột nghiệp vụ của bảng raw, đúng thứ tự trong migration

    # Đường mock đọc gì từ mock_server:
    #   "json" — nguồn thật là API: mock trả JSON cùng hình dạng (render_api_page), parse() dùng lại.
    #   "html" — nguồn thật là trang web: mock trả trang HTML 20 dòng/trang, base tự parse bảng.
    mock_format: Literal["json", "html"] = "json"
    mock_page_size: int = 20  # chỉ dùng cho mock_format = "json"

    # ------------------------------------------------------------------ phải viết

    @abstractmethod
    def fetch_live(self, since: date | None) -> Iterator[RawPage]:
        """Gọi nguồn thật, trả về từng trang gốc. Dùng http_client.get() để tôn trọng rate limit."""

    @abstractmethod
    def parse(self, page: RawPage) -> Iterator[dict]:
        """Trang gốc -> bản ghi thô (dict giá trị chuỗi). Không làm sạch, không ép kiểu."""

    @abstractmethod
    def describe(self) -> SourceMeta:
        """url, license, tần suất cập nhật, chủ sở hữu — ghi vào meta.source."""

    # ------------------------------------------------------------------ có thể override

    def render_api_page(self, records: list[dict], page: int, page_size: int, total: int) -> dict:
        """Hình dạng JSON của API thật, để mock_server phát lại. Nguồn API phải override cho khớp
        đúng response thật, vì parse() sẽ đọc lại chính hình dạng này ở đường mock."""
        return {"page": page, "page_size": page_size, "total": total, "data": records}

    def row_hash(self, record: dict) -> str:
        """Khóa định danh bản ghi để khử trùng lặp giữa các lô.

        Mặc định: md5 của toàn bộ bản ghi dạng JSON sắp khóa. Override nếu nguồn có khóa ổn định.
        """
        canonical = json.dumps(record, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(canonical.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------ không sửa

    def fetch(self, since: date | None, mode: SourceMode) -> Iterator[RawPage]:
        if mode == "live":
            yield from self.fetch_live(since)
        elif mode == "mock":
            if since is not None:
                raise ValueError(
                    "Mode mock phát lại snapshot live gần nhất, không lọc --since. "
                    "Chạy live với --since trước, rồi mới chạy mock."
                )
            yield from self._fetch_mock()
        else:
            raise ValueError(f"mode phải là một trong {SOURCE_MODES}, nhận {mode!r}")

    def records(self, page: RawPage) -> Iterator[dict]:
        if page.mode == "mock" and self.mock_format == "html":
            yield from parse_mock_html(page.content)
        else:
            yield from self.parse(page)

    def _fetch_mock(self) -> Iterator[RawPage]:
        base = os.environ.get("MOCK_SERVER_URL", "http://localhost:8001").rstrip("/")
        if self.mock_format == "json":
            url = f"{base}/api/{self.name}"
            params: dict | None = {"page": 1, "page_size": self.mock_page_size}
        else:
            url, params = f"{base}/{self.name}", {"page": 1}
        while url:
            resp = http_client.get(url, params=params)
            yield RawPage(
                url=str(resp.url),
                content=resp.content,
                content_type=resp.headers.get("content-type", ""),
                mode="mock",
            )
            nxt = resp.links.get("next", {}).get("url")
            url = str(resp.url.join(nxt)) if nxt else ""
            params = None


class _RecordTableParser(HTMLParser):
    """Đọc <table id="records"> của mock_server: <th> là tên cột, <td data-null> là NULL."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_table = False
        self.headers: list[str] = []
        self.rows: list[list[str | None]] = []
        self._cell: list[str] | None = None
        self._cell_null = False
        self._row: list[str | None] | None = None
        self._in_th = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and attrs.get("id") == "records":
            self.in_table = True
        elif not self.in_table:
            return
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell, self._cell_null, self._in_th = [], "data-null" in attrs, tag == "th"

    def handle_endtag(self, tag):
        if not self.in_table:
            return
        if tag == "table":
            self.in_table = False
        elif tag in ("td", "th") and self._cell is not None:
            value = None if self._cell_null else "".join(self._cell)
            if self._in_th:
                self.headers.append(value or "")
            elif self._row is not None:
                self._row.append(value)
            self._cell = None
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)


def parse_mock_html(content: bytes) -> Iterator[dict]:
    parser = _RecordTableParser()
    parser.feed(content.decode("utf-8"))
    for row in parser.rows:
        yield dict(zip(parser.headers, row, strict=True))
