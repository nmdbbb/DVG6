# Decision log

Mỗi quyết định có đánh đổi là một dòng. Cả nhóm ghi, Data Architect duyệt. Đổi một quyết định cũ thì thêm dòng mới trỏ về số cũ, không sửa dòng cũ.

| # | Ngày | Quyết định | Lý do | Đánh đổi | Người chốt |
|---|------|-----------|-------|----------|-----------|
| 1 | 2026-10-05 | Dùng PostgreSQL 16 thay DuckDB | Cần mô hình client-server, nhiều người ghi, có user/quyền/schema như warehouse thật | Tốn thời gian setup; giải quyết bằng Docker Compose | Nhóm (khung repo) |
| 2 | 2026-10-05 | Dùng dbt-core + dbt-postgres cho transform | Có sẵn test, lineage graph (`make lineage`), `persist_docs` ghi mô tả thành `COMMENT ON` | Cả nhóm mất một buổi làm quen dbt | Nhóm (khung repo) |
| 3 | 2026-10-05 | Chọn polars (không dùng pandas) cho ingestion | Nhanh hơn trên file lớn; một thư viện cho cả nhóm | Ai quen pandas phải đọc lại cú pháp | Nhóm (khung repo) |
| 4 | 2026-10-05 | Mọi lệnh `make` chạy trong container; etl và api dùng chung một image Python | Máy chỉ cần git + Docker + make; không ai lệch phiên bản Python/dbt | Lần build đầu ~1–2 phút; debug phải `docker compose run --rm etl sh` | Khung M1 |
| 5 | 2026-10-05 | `db/migrations/` chỉ quản schema, `raw`, `meta`; `staging`/`core`/`analytics` do dbt dựng | Tránh hai nơi cùng định nghĩa một bảng. Khung gốc dự kiến `004_core_dimensions`–`006_analytics_views`, đã bỏ vì trùng việc với dbt | DDL của core không nằm trong `db/`; xem `transform/models/core/` + `schema.yml` | Khung M3 |
| 6 | 2026-10-05 | `dim_entity.entity_key` = `row_number()` theo `entity_id`, dựng lại toàn bảng mỗi lần chạy, thay vì `identity` | dbt dựng lại dim và fact cùng lúc nên khóa luôn khớp; đơn giản, tất định | Khóa của một thực thể có thể đổi khi thêm thực thể mới. Nếu chuyển fact sang incremental phải đổi sang khóa ổn định (snapshot hoặc hash) | Khung M3 |
| 7 | 2026-10-05 | `etl_writer` chỉ có `SELECT, INSERT` trên `raw` | Nguyên tắc "raw bất biến" được database ép, không phụ thuộc kỷ luật | Sửa dữ liệu raw sai phải dùng tài khoản admin và ghi lý do vào đây | Khung M2 |
| 8 | 2026-10-05 | `meta.quality_run` có khóa `check_result_id`, `run_id` gom các check cùng một lần chạy | Một lần chạy có nhiều check; khung gốc ghi `run_id pk` thì mỗi lần chạy chỉ có một dòng | Thêm một cột | Khung M3 |
| 9 | 2026-10-05 | `quality.runner` chạy luôn `dbt test` và ghi kết quả vào `meta.quality_run` | Dashboard thấy cả check của dbt lẫn `rules.yml` ở một chỗ, một exit code duy nhất | `make quality` chậm hơn vài giây | Khung M3 |
| 10 | 2026-10-05 | Số dòng và tỉ lệ NULL của mọi bảng được `etl_writer` đo, ghi vào `meta.table_profile`/`meta.column_profile`; API chỉ đọc meta | API (`api_reader`) không được SELECT raw/core, nhưng Overview và Catalog cần số liệu của mọi tầng | Số liệu catalog chỉ mới tới lần `make quality` gần nhất | Khung M4 |
| 11 | 2026-10-05 | `transform/profiles.yml` được commit, chỉ chứa `env_var()` | Không có bí mật trong file; bỏ một bước copy tay (khung gốc ghi `profiles.yml.example`) | Ai đổi target phải sửa file chung | Khung M3 |
| 12 | 2026-10-05 | Frontend gọi API qua proxy `/api` của Vite (`VITE_API_BASE_URL=/api`) | Không phải bật CORS; cùng một URL trong Docker và ngoài Docker | Khi deploy production phải cấu hình reverse proxy tương tự | Khung M4 |
| 13 | 2026-10-05 | Gộp 6 vai của khung gốc thành 5 vai: Analysis Lead và Analysis thành "Analysis & Quality Owner" | Nhóm chọn 5 vai; phân tích và gác chất lượng cùng một mạch (người đặt ngưỡng cũng là người dùng số liệu) | Người giữ vai này vừa viết notebook vừa duyệt kết luận của chính mình → PR `analysis/` cần thêm một người review chéo | Khung repo |
| 14 | 2026-10-05 | Branch protection `main`: bắt buộc PR + 1 approve + Code Owners + CI `lint`, `pipeline` xanh; admin vẫn được bypass (`enforce_admins = false`) | Khi chưa đủ thành viên trên GitHub, chủ repo vẫn phải merge được | Bật `enforce_admins` khi cả nhóm đã vào repo (xem `docs/runbook.md`) | Khung repo |
