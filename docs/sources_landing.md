# Nhật ký file tải tay (landing)

> Mỗi file nguồn tải tay một dòng. Hiện ghi thủ công từ kết quả `python -m ingestion.inspect_vaers`; `make landing-register` chưa được triển khai.
> Thư mục `data/` không commit, nên bảng này là bằng chứng duy nhất trong repo về việc nhóm đã dùng chính xác file nào.

Ai cần dựng lại warehouse phải tải đúng file có sha256 trùng bảng dưới. sha256 lệch nghĩa là nguồn đã đổi dữ liệu — khi đó thêm dòng mới, **không sửa dòng cũ**, và ghi một dòng vào `decision_log.md`.

| # | Nguồn | File | Ngày tải | Người tải | Kích thước | sha256 |
|---|---|---|---|---|---|---|
| 1 | vaers | `data/landing/vaers/2026-10-15/2021VAERSData.zip` | 2026-10-15 (theo thư mục landing) | Người dùng cung cấp | 180005429 bytes | `40035677f13798a84a88b77b74d78f5dbeca8151085e58d4a68d204d4cf40f74` |
| 2 | vaers | `data/landing/vaers/2026-10-15/2022VAERSData.zip` | 2026-10-15 (theo thư mục landing) | Người dùng cung cấp | 66338262 bytes | `161cef901dcf5e6fabf7feba3d0094518a25d51fd71f8e5b357ccdb7d69d02e6` |
| 3 | vaers | `data/landing/vaers/2026-10-15/2023VAERSData.zip` | 2026-10-15 (theo thư mục landing) | Người dùng cung cấp | 26357544 bytes | `47c570a2add43ef06196793040b7832f6ee241e007f136a66e30227d6f7355da` |
| 4 | vaers | `data/landing/vaers/2026-10-15/2024VAERSData.zip` | 2026-10-15 (theo thư mục landing) | Người dùng cung cấp | 13924124 bytes | `8ba2bc09e853044081ebe9b13104be55fa3d96f39f5c6974a35fba993badf284` |
| 5 | vaers | `data/landing/vaers/2026-10-15/2025VAERSData.zip` | 2026-10-15 (theo thư mục landing) | Người dùng cung cấp | 11029527 bytes | `7692177d8c08ee2f16633539d5cfb4a426bcf7061fb86dc2d3230c4df02d3c1b` |
| 6 | vaers | `data/landing/vaers/2026-10-15/2026VAERSData.zip` | 2026-10-15 (theo thư mục landing) | Người dùng cung cấp | 5012704 bytes | `5d01162feb638d52e2be96e7917264c213b66fe7f9b7bbc692ef522e6a3bdfc7` |
