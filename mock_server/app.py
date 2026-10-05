"""Mock server: đường dự phòng của ingestion, phát lại bản gốc đã tải từ nguồn thật.

    GET /health                              healthcheck (không trễ, không tính rate limit)
    GET /                                    danh sách nguồn + snapshot đang phát
    GET /{source}?page=N                     trang HTML, 20 dòng/trang, <a rel="next">
    GET /api/{source}?page=N&page_size=M     JSON cùng hình dạng API thật (connector.render_api_page)

Mọi trang có header `Link: <...>; rel="next"` và `X-Mock-Snapshot: <batch_id>`.
Mô phỏng điều kiện thật ở mức vừa phải: trễ 200–500 ms mỗi request, quá 60 request/phút/client
trả 429 kèm Retry-After. Không trả lỗi 500 ngẫu nhiên.
"""

from __future__ import annotations

import asyncio
import html
import math
import os
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ingestion import registry
from mock_server import seed


@dataclass
class Settings:
    latency_min_ms: int = int(os.environ.get("MOCK_LATENCY_MIN_MS", 200))
    latency_max_ms: int = int(os.environ.get("MOCK_LATENCY_MAX_MS", 500))
    rate_limit_per_min: int = int(os.environ.get("MOCK_RATE_LIMIT_PER_MIN", 60))
    html_page_size: int = 20
    json_max_page_size: int = 1000


settings = Settings()


class RateLimiter:
    """Cửa sổ trượt 60 giây theo địa chỉ client."""

    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, client: str) -> float | None:
        """None nếu được phép; ngược lại số giây phải chờ."""
        if settings.rate_limit_per_min <= 0:
            return None
        now = time.monotonic()
        window = self.hits[client]
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_min:
            return 60 - (now - window[0])
        window.append(now)
        return None

    def reset(self) -> None:
        self.hits.clear()


limiter = RateLimiter()
app = FastAPI(title="QTDL mock server", version="0.1.0")


@app.middleware("http")
async def realistic_conditions(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)
    wait = limiter.check(request.client.host if request.client else "unknown")
    if wait is not None:
        retry = max(1, math.ceil(wait))
        return JSONResponse(
            {
                "detail": f"Rate limit {settings.rate_limit_per_min} request/phút. Thử lại sau {retry}s."
            },
            status_code=429,
            headers={"Retry-After": str(retry)},
        )
    if settings.latency_max_ms > 0:
        lo, hi = settings.latency_min_ms, max(settings.latency_min_ms, settings.latency_max_ms)
        await asyncio.sleep(random.uniform(lo, hi) / 1000)
    return await call_next(request)


def _snapshot(source: str) -> seed.Snapshot:
    try:
        snap = seed.load(source)
    except KeyError:
        raise HTTPException(404, f"Không có nguồn '{source}'") from None
    if snap is None:
        raise HTTPException(
            503,
            f"Chưa có snapshot live cho '{source}'. Chạy `make ingest SOURCE_MODE=live` trước.",
        )
    return snap


def _page_bounds(total: int, page: int, size: int) -> tuple[int, int, bool]:
    n_pages = max(1, math.ceil(total / size))
    if page > n_pages:
        raise HTTPException(404, f"Trang {page} vượt quá {n_pages} trang")
    return (page - 1) * size, page * size, page < n_pages


def _links(path: str, page: int, has_next: bool, extra: str = "") -> str:
    links = []
    if has_next:
        links.append(f'<{path}?page={page + 1}{extra}>; rel="next"')
    if page > 1:
        links.append(f'<{path}?page={page - 1}{extra}>; rel="prev"')
    return ", ".join(links)


def _headers(snap: seed.Snapshot, link: str) -> dict:
    headers = {"X-Mock-Snapshot": snap.batch_id}
    if link:
        headers["Link"] = link
    return headers


@app.get("/health")
def health():
    # Luôn 200 khi server chạy; tình trạng snapshot chỉ để xem, không làm container unhealthy.
    snapshots = {}
    for s in seed.sources():
        try:
            snap = seed.load(s)
            snapshots[s] = snap.batch_id if snap else None
        except Exception as exc:  # noqa: BLE001
            snapshots[s] = f"error: {exc}"
    return {"status": "ok", "snapshots": snapshots}


@app.get("/", response_class=HTMLResponse)
def index():
    rows = []
    for s in seed.sources():
        snap = seed.load(s)
        info = (
            f"{len(snap.records)} bản ghi · lô <code>{snap.batch_id}</code> · {snap.finished_at}"
            if snap
            else "chưa có snapshot live"
        )
        rows.append(
            f'<li><a href="/{s}?page=1">{s}</a> (<a href="/api/{s}">JSON</a>) — {info}</li>'
        )
    return _html(
        "Mock server", f"<p>Phát lại bản gốc từ <code>data/raw/</code>.</p><ul>{''.join(rows)}</ul>"
    )


@app.get("/api/{source}")
def api_page(
    source: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.json_max_page_size),
):
    snap = _snapshot(source)
    start, end, has_next = _page_bounds(len(snap.records), page, page_size)
    body = registry.get(source).render_api_page(
        snap.records[start:end], page, page_size, len(snap.records)
    )
    link = _links(f"/api/{source}", page, has_next, f"&page_size={page_size}")
    return JSONResponse(body, headers=_headers(snap, link))


@app.get("/{source}", response_class=HTMLResponse)
def html_page(source: str, page: int = Query(1, ge=1)):
    snap = _snapshot(source)
    size = settings.html_page_size
    start, end, has_next = _page_bounds(len(snap.records), page, size)

    head = "".join(f"<th>{html.escape(c)}</th>" for c in snap.columns)
    body = []
    for rec in snap.records[start:end]:
        cells = []
        for c in snap.columns:
            v = rec.get(c)
            cells.append("<td data-null></td>" if v is None else f"<td>{html.escape(str(v))}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    nav = []
    if page > 1:
        nav.append(f'<a rel="prev" href="?page={page - 1}">← Trang trước</a>')
    if has_next:
        nav.append(f'<a rel="next" href="?page={page + 1}">Trang sau →</a>')
    n_pages = max(1, math.ceil(len(snap.records) / size))
    content = (
        f"<p>Trang {page}/{n_pages} · {len(snap.records)} bản ghi · lô {snap.batch_id}</p>"
        f'<table id="records"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'
        f'<nav class="pager">{" ".join(nav)}</nav>'
    )
    return HTMLResponse(
        _html(f"{source} — trang {page}", content),
        headers=_headers(snap, _links(f"/{source}", page, has_next)),
    )


def _html(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">'
        f"<title>{html.escape(title)}</title>"
        "<style>body{font:14px system-ui,sans-serif;margin:24px}"
        "table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:2px 6px;"
        "white-space:pre}</style></head>"
        f"<body><h1>{html.escape(title)}</h1>{body}</body></html>"
    )
