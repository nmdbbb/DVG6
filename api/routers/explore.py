"""Truy vấn fact theo filter dimension — làm ở M6, sau khi chốt topic.

Endpoint dự kiến (docs gốc):
    GET /dimensions/{dim}                          giá trị một dimension cho dropdown
    GET /explore/facts?dim=&from=&to=&group_by=    độ đo đã tổng hợp

Chỉ đọc analytics.v_*; tham số qua Pydantic và bind parameter, không nối chuỗi SQL.
"""

from fastapi import APIRouter

router = APIRouter(tags=["explore"])
