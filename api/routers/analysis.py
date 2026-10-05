"""Kết quả phân tích đã tính sẵn — làm ở M6.

Endpoint dự kiến (docs gốc):
    GET /analysis/correlation            ma trận tương quan
    GET /analysis/regression/{model}     hệ số, sai số chuẩn, p-value, R²

Notebook trong analysis/ ghi kết quả vào bảng analytics, API chỉ đọc bảng đó.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/analysis", tags=["analysis"])
