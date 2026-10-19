# Tình hình hệ thống

Đo trên máy Data Architect ngày 2026-10-19, sau `make up`, `make migrate`, `make dashboard` với code ở `main` (có migration 006/007). Đây là trạng thái **đang chạy**, không phải trạng thái repo.

**Tóm lại:** hệ thống chạy được đầu-cuối nhưng chỉ có dữ liệu **giả** (`source_demo`, 5.000 dòng). Bảng cho VAERS và openFDA đã được tạo nhưng **đều rỗng**; chưa có dữ liệu thật nào đi qua staging, core hay lên dashboard.

## 1. Dịch vụ

| Dịch vụ | Địa chỉ | Tình trạng |
|---|---|---|
| Postgres 16 (`db`) | localhost:5432 | healthy |
| mock_server | http://localhost:8001 | healthy |
| API (FastAPI) | http://localhost:8000/docs | healthy |
| Web (React) | http://localhost:5173 | HTTP 200 |
| pgAdmin | profile `tools`, không bật mặc định | tắt |

## 2. Database `qtdl`

`meta.schema_version` có **7 migration** (001–007), chạy lại `make migrate` thì 0 mới.

| Schema | Bảng / view | Số dòng | Nguồn dữ liệu |
|---|---|---|---|
| raw | `source_demo_records` | 5.000 | dữ liệu giả |
| raw | `vaers_data`, `vaers_vax`, `vaers_symptoms` | **0** | chưa nạp |
| raw | `openfda_substances` | **0** | chưa nạp |
| staging | `stg_source_demo__records` (view) | 5.000 | giả |
| core | `dim_entity` | 21 (20 thực thể + dòng unknown) | giả |
| core | `fct_main` | 4.926 (mất 74 dòng thiếu `record_id` / trùng, trong ngưỡng 5%) | giả |
| analytics | `v_measure_by_category_month` (view) | 309 | giả |
| meta | `ingestion_batch` 1 · `ingestion_batch_row` 5.000 · `source` 1 · `quality_run` 22 · `table_profile` 9 · `column_profile` 15 | | |

Chưa tồn tại: mọi bảng `dim_*` / `fct_*` của VAERS (vaccine, symptom, allergen, age_group, sex, state, date, `fct_report*`, `report_duplicate_map`) và mọi view `v_ae_*` phục vụ phân tích.

Phân quyền: 3 role `etl_writer`, `api_reader`, `analyst` được cấp lại sau mỗi lần migrate.

## 3. Ingestion

| Nguồn | Trong registry | Đã nạp | Ghi chú |
|---|---|---|---|
| `source_demo` | có | 1 lô `live` thành công, 5.000 dòng (2026-10-18) | chạy lại ra `new_rows=0` |
| `vaers_data`, `vaers_symptoms`, `vaers_vax` | **không** | 0 | connector chưa có trong code đang chạy; bảng raw đã sẵn sàng |
| `openfda` | **không** | 0 | như trên |

- Đường mock: `make mock-check` cho `source_demo` đạt (số dòng và tập `_row_hash` khớp).
- File tải tay: `data/landing/` **rỗng**, `docs/sources_landing.md` chưa có dòng nào. `make landing-verify` trả "0 file khớp checksum"; `make ingest` đã gọi nó trước khi nạp.
- `data/raw/` chỉ có snapshot của `source_demo`.

## 4. Chất lượng

- Lần chạy `make quality` gần nhất: **22/22 check đạt** (test dbt + `rules.yml`), gồm khóa chính `dim_entity`, không mồ côi trong `fct_main`, đối chiếu số dòng raw → core.
- Toàn bộ check chỉ nhắm vào bảng của `source_demo`. **Chưa có check nào cho dữ liệu VAERS** (miền giá trị, đối chiếu số dòng, tỉ lệ trùng lặp, chuẩn hóa dị ứng).
- Cơ chế chặn đã chứng minh: `make demo-break` làm `make quality` exit 1.
- `make test`: 40 test đạt. `make lint`: sạch.

## 5. API và dashboard

| Endpoint | Tình trạng | Ghi chú |
|---|---|---|
| `/sources`, `/batches`, `/quality`, `/quality/runs`, `/layers` | chạy | trả dữ liệu của `source_demo` |
| `/catalog/tables`, `/catalog/tables/{name}/columns` | chạy | liệt kê **16 bảng/view**, gồm 4 bảng VAERS/openFDA mới với `row_count = 0` |
| `/explore/facts`, `/dimensions/{dim}`, `/analysis/*` | **404** | chưa cài |

| Trang web | Tình trạng |
|---|---|
| Tổng quan, Sức khỏe pipeline, Catalog | chạy, hiển thị dữ liệu giả và 4 bảng raw mới (rỗng) |
| Khám phá, Phân tích | trang giữ chỗ ("M6") |

## 6. Phân tích

`analysis/notebooks/` và `analysis/reports/` trống. Chưa có notebook, bảng kết quả hay hình nào.

## 7. Để chạy dữ liệu VAERS thật, hệ thống còn thiếu

1. Connector VAERS và openFDA trong registry, cộng file ZIP đã đăng ký bằng `make landing-register SOURCE=vaers`.
2. Model staging và core cho VAERS, kèm khử trùng lặp theo `rule_version=1`.
3. Check chất lượng cho dữ liệu VAERS.
4. View `analytics`, API `/explore` và `/analysis`, hai trang web còn lại, các notebook A1–A8.
5. Gỡ `source_demo` khỏi registry, dbt và CI khi bước 1–3 chạy được.

## 8. Tái hiện số liệu trên

```bash
make up && make migrate && make ingest && make transform && make quality && make dashboard
docker compose exec db psql -U qtdl -d qtdl -c "select * from meta.schema_version;"
curl localhost:8000/catalog/tables
```
