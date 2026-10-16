# Nhật ký file tải tay (landing)

> Mỗi file nguồn tải tay một dòng. Hiện ghi thủ công từ kết quả `python -m ingestion.inspect_vaers`; `make landing-register` chưa được triển khai.
> Thư mục `data/` không commit, nên bảng này là bằng chứng duy nhất trong repo về việc nhóm đã dùng chính xác file nào.

Ai cần dựng lại warehouse phải tải đúng file có sha256 trùng bảng dưới. sha256 lệch nghĩa là nguồn đã đổi dữ liệu — khi đó thêm dòng mới, **không sửa dòng cũ**, và ghi một dòng vào `decision_log.md`.

| # | Nguồn | File | Ngày tải | Người tải | Kích thước | sha256 |
|---|---|---|---|---|---|---|
| 1 | vaers | `data/landing/vaers/2026-10-15/2021VAERSData.zip` | 2026-10-15 (theo thư mục landing) | Người dùng cung cấp | 180005429 bytes | `40035677f13798a84a88b77b74d78f5dbeca8151085e58d4a68d204d4cf40f74` |
