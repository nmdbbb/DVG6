"""HTTP client dùng chung cho connector: timeout, User-Agent, tôn trọng 429 (Retry-After).

Dùng cho cả nguồn thật (live) lẫn mock_server, nên connector được thử với rate limit ngay từ đầu.
"""

from __future__ import annotations

import time

import httpx

USER_AGENT = "qtdl-warehouse/0.1 (student project; contact via repo issues)"
MAX_RETRIES = 5

_client: httpx.Client | None = None


def client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
    return _client


def get(url: str, params: dict | None = None) -> httpx.Response:
    """GET có retry khi 429 hoặc lỗi mạng tạm thời. Lỗi khác (4xx/5xx) raise ngay."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client().get(url, params=params)
        except httpx.TransportError:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(2**attempt)
            continue
        if resp.status_code == 429 and attempt < MAX_RETRIES:
            time.sleep(_retry_after(resp, default=2**attempt))
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError("unreachable")


def _retry_after(resp: httpx.Response, default: float) -> float:
    try:
        return max(float(resp.headers.get("Retry-After", default)), 0.5)
    except ValueError:
        return default
