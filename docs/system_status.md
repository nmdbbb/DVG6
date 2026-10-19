# Hiện trạng hệ thống

Cập nhật 2026-10-19 bởi Data Architect. Tổng hợp từ `main`, `liem-dev` và `feat/openfda-crawler` (PR #38). PR #39 của Data Architect đã merge vào `main` (commit `16eaa91`).

**Tóm lại:** khung hạ tầng M1–M4 chạy được đầu-cuối trên dữ liệu giả `source_demo`. Với dữ liệu VAERS thật mới có **hợp đồng dữ liệu** và **migration raw** trên `main`, còn **connector nạp** vẫn nằm ở hai branch chưa merge; staging, core, quality, phân tích và dashboard của VAERS chưa ai bắt đầu.

## 1. Đã merge vào `main`

| Tầng | Có gì | Dùng dữ liệu |
|---|---|---|
| Hạ tầng | Docker Compose (db, etl, mock_server, api, web, pgadmin), Makefile, CI `lint` + `pipeline`, branch protection, CODEOWNERS | — |
| Database | 5 migration (schema `raw`/`staging`/`core`/`analytics`/`meta`, bảng `meta.*`, bảng raw demo, profile, `source_mode`), 3 role phân quyền (`etl_writer`, `api_reader`, `analyst`) | — |
| Ingestion | Khung connector (`base.py`, `loader.py`, `http_client.py`, `cli.py`, `registry.py`), chống nạp lại bằng `_row_hash`, lưu bản gốc từng trang vào `data/raw/` | `source_demo` |
| Mock server | Phát lại snapshot live (HTML và JSON), giả lập trễ và giới hạn 60 request/phút, `make mock-check` so lô live với lô mock | `source_demo` |
| Transform | dbt: `stg_source_demo__records` → `dim_entity`, `fct_main` → `v_measure_by_category_month` | `source_demo` |
| Quality | `quality/runner.py`, `rules.yml` (3 check bắt buộc + bổ sung) và test dbt; ghi `meta.quality_run`, profile bảng, sinh `quality_report.md`; `make demo-break` chứng minh gate chặn pipeline | `source_demo` |
| API | FastAPI: `/sources`, `/batches`, `/quality`, `/quality/runs`, `/layers`, catalog bảng và cột (đọc từ `COMMENT ON`) | mọi bảng |
| Web | React: Tổng quan, Sức khỏe pipeline, Catalog; Khám phá và Phân tích còn là trang giữ chỗ (M6) | `source_demo` |
| Data contract (PR #39) | Grain 13 bảng core, quy tắc NULL, quy ước ngày VAERS, quy tắc khử trùng lặp `rule_version=1`, `docs/system_status.md`, decision #30–#34 | VAERS |
| Landing | `make landing-register` / `landing-verify` (`scripts/landing.py`, 8 test); `make ingest` kiểm sha256 file tải tay trước khi nạp | VAERS |
| Migration | `006_vaers_raw_tables.sql` (3 bảng VAERS), `007_openfda_substances.sql`; `make reset` trên Postgres trống ra 7 migration, mọi cột raw có comment | VAERS, openFDA |
| Tài liệu | business case, analysis plan (A1–A8), schema đề xuất, kế hoạch 36 issue (M5–M7) | VAERS |

## 2. Đang chờ merge

| Branch / PR | Người | Nội dung | Tình trạng |
|---|---|---|---|
| `liem-dev` | Duy Liem | 3 connector `vaers_data`, `vaers_symptoms`, `vaers_vax` đọc ZIP 2021 (cp1252, kiểm sha256), `ingestion/inspect_vaers.py`, `docs/vaers_ingestion.md`, 19 test, sửa healthcheck mock | **Chưa mở PR, chưa biết `006` đã nằm trên `main` và không được sửa nữa.** Đã nạp thật vào Postgres của Liem (symptoms 1.030.201 dòng). Chưa chạy `make mock-check` cho 3 nguồn |
| `feat/openfda-crawler` (PR #38) | MinhAgain | Connector `openfda` (phân trang, `skip` ≤ 25.000), hash theo `spl_id`, mock JSON, test | Đã comment 2026-10-19 yêu cầu **xóa `006_openfda_substances.sql` và `README_PATCH.txt`**, rebase lên `main`; chưa có commit mới. Snapshot không phủ hết ~262 nghìn nhãn |

Số liệu nguồn VAERS 2021 (Liem đo): DATA 768.704 · SYMPTOMS 1.030.201 · VAX 813.432 dòng, trước khi lọc COVID19.

### Issue role 1 (`role:architect`)

| Issue | Trạng thái |
|---|---|
| #2 Data contract và star schema | Đã viết và merge. Còn thiếu chữ ký Analysis Lead cho decision #31 trước khi đóng |
| #3 Migration raw | Đã merge (006 + 007). Chưa kiểm Catalog hiện 4 bảng mới trên dashboard thật; chờ connector merge để thử nạp |
| #4 `make landing-register` | Đã merge. Chưa đăng ký file thật vào `sources_landing.md` (dòng của Liem nằm ở `liem-dev`) |
| #34 Runbook và nghiệm thu tái tạo | Bị block bởi staging/core VAERS |
| #37 Bật `enforce_admins` | Bị block đến khi cả nhóm vào repo |

Chưa đóng issue nào trên GitHub.

## 3. Chưa có

| Việc | Issue | Phụ thuộc | Ghi chú |
|---|---|---|---|
| Staging VAERS + openFDA, unpivot 5 cột triệu chứng | #11, #12 | `liem-dev` và PR #38 phải merge | **Đường găng.** Staging phải lọc bằng `EXISTS` trên `meta.ingestion_batch_row` (xem `vaers_ingestion.md`) |
| 6 dimension, `dim_allergen` (từ điển openFDA) | #13, #14 | #11, #12 | |
| `fct_report` + khử trùng lặp, 3 fact con, `fct_report_raw`, `report_duplicate_map` | #15, #16 | #13, #14 | Theo `analysis_plan.md` §5 |
| Check chất lượng (miền giá trị, đối chiếu số dòng, trùng lặp, chuẩn hóa dị ứng, ngưỡng thống kê) | #17–#20 | #15, #16 | `rules.yml` vẫn chỉ có check của `source_demo` |
| Analytics view cho từng biểu đồ | #22 | #16 | |
| Phân tích A1–A8 (tần suất, heatmap, chi-square, phân cụm, ARM, PCA, tác động làm sạch) | #23–#29 | #22 | `analysis/notebooks/` còn trống |
| API `/dimensions`, `/explore/facts`, `/analysis/*`; trang Khám phá, Phân tích; Overview và Catalog với nguồn thật | #21, #30–#33 | #22, #29 | |
| `mock_server` phát lại snapshot VAERS lớn; hoàn thiện `sources.md` | #6, #8, #9 | `liem-dev`, PR #38 | |
| Gỡ `source_demo` khỏi registry, CI và dbt | #10 | #11–#16 chạy được | Đến lúc đó CI vẫn dùng `SOURCE=source_demo` vì ZIP VAERS không có trên CI |
| Runbook và nghiệm thu tái tạo trên máy trống | #34 | tất cả trên | Hiện `make all` chỉ tái tạo được phần `source_demo` |
| Báo cáo cuối, hình và bảng | #35, #36 | #29 | |
| Bật `enforce_admins` | #37 | cả nhóm vào repo | |

## 4. Rủi ro và điểm cần quyết

1. **Không có mẫu số.** `data.cdc.gov` trả 403 nên chỉ tính được tần suất tương đối, không tính được tỉ lệ trên 100.000 liều (decision #24). Báo cáo không được dùng chữ "nguy cơ" hay "gây ra".
2. **Tên cột raw VAERS viết hoa, có dấu ngoặc kép** (decision #29 của Liem, trái với chữ "viết thường" trong issue #3). Staging phải đổi tên; đã chấp nhận vì connector đã nạp hàng triệu dòng.
3. **Lô `failed` trong raw của Liem:** 874.900 dòng symptoms gắn lô gốc `failed` nhưng hash đã được xác nhận trong lô `success`. Staging nào lọc qua `_batch_id` sẽ mất 85% dữ liệu.
4. **CI không chạy được VAERS** (không có ZIP): mọi thay đổi VAERS chỉ được kiểm bằng test nhỏ và chạy tay. Đừng coi CI xanh là bằng chứng VAERS đúng.
5. **Khử trùng lặp bảo thủ** (decision #31): tỉ lệ trùng lặp có thể thấp hơn 29% của bài báo; phải báo cáo kèm độ nhạy.
6. **Số 29 trong decision_log** trên `liem-dev` và số 30–34 trên PR #39 đánh liền nhau; hai branch merge theo thứ tự nào cũng xung đột nhỏ ở cuối bảng, giữ cả hai bộ dòng.

## 5. Cách xem lại

```bash
make up && make migrate     # 7 migration, 5 bảng raw (cần 006/007 từ main) (source_demo + 3 VAERS + openfda)
make landing-verify         # kiểm sha256 file tải tay
make all                    # pipeline source_demo đầu-cuối
make dashboard              # http://localhost:5173
```
