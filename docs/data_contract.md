# Data contract

> Bản nháp do khung repo sinh ra. Data Architect chốt sau buổi chọn topic; sau khi chốt, sửa file này phải báo cả nhóm.

## 1. Bảng core và grain

Phạm vi dữ liệu vào `core` (decision #28): báo cáo có `RECVDATE` trong 2021, có ít nhất một dòng vắc xin `VAX_TYPE = 'COVID19'`, trong nước Mỹ. Phần lọc này làm ở staging; `raw` giữ nguyên mọi dòng.

**Dimension** (mỗi bảng có dòng unknown `*_key = -1`)

| Bảng | Grain (một câu) |
|---|---|
| `core.dim_vaccine` | Một dòng cho mỗi sản phẩm vắc xin khác nhau `(vax_type, vax_manu chuẩn hóa, vax_name)` |
| `core.dim_symptom` | Một dòng cho mỗi thuật ngữ MedDRA Preferred Term đã chuẩn hóa |
| `core.dim_allergen` | Một dòng cho mỗi chất gây dị ứng đã chuẩn hóa (`canonical_name`), cộng `UNMAPPED` |
| `core.dim_age_group` | Một dòng cho mỗi nhóm tuổi trong 7 nhóm cố định, cộng `UNKNOWN` |
| `core.dim_sex` | Một dòng cho mỗi giới tính `M` / `F` / `U` |
| `core.dim_state` | Một dòng cho mỗi bang / lãnh thổ Mỹ (mã 2 chữ cái), cộng `UNKNOWN` |
| `core.dim_date` | Một dòng cho mỗi ngày dương lịch từ 2020-01-01 đến 2025-12-31, cộng `UNKNOWN` |

**Fact**

| Bảng | Grain (một câu) |
|---|---|
| `core.fct_report` | Một dòng cho mỗi báo cáo **đã khử trùng lặp** (`vaers_id` duy nhất) |
| `core.fct_report_raw` | Một dòng cho mỗi báo cáo **chưa khử trùng lặp** (`vaers_id` duy nhất; là tập cha của `fct_report`) |
| `core.fct_report_vaccine` | Một dòng cho mỗi `(report_key, vaccine_key, dose_series)` |
| `core.fct_report_symptom` | Một dòng cho mỗi `(report_key, symptom_key)`; một triệu chứng lặp trong cùng báo cáo chỉ tính một lần |
| `core.fct_report_allergen` | Một dòng cho mỗi `(report_key, allergen_key)` |
| `core.report_duplicate_map` | Một dòng cho mỗi báo cáo bị coi là trùng, trỏ về `vaers_id` được giữ |

Ba fact con (`vaccine`, `symptom`, `allergen`) chỉ chứa báo cáo có mặt trong `fct_report`. Muốn phân tích trên tập chưa khử trùng lặp (Q5) thì nối qua `fct_report_raw`, không tự suy ra từ `raw`.

Thêm bảng core mới phải ghi grain vào đây **trước** khi viết model. `dim_entity` / `fct_main` là bảng của `source_demo`; Transform xóa cùng lúc gỡ `source_demo` khỏi registry (issue #10).

## 2. Khóa nối giữa các nguồn

- Nối qua khóa tự nhiên đã chuẩn hóa ở staging (`trim` + `upper`), không nối qua tên hiển thị.
- Giá trị không khớp dimension → trỏ `-1` (unknown), không loại dòng.
- Hai nguồn cho giá trị khác nhau về cùng một sự kiện → ghi quy tắc ưu tiên vào `decision_log.md`.

## 3. Quy ước

| Mục | Quy ước |
|---|---|
| Tên bảng, cột | `snake_case`, số ít |
| Dimension | `dim_<thực thể>`, khóa thay thế `<thực thể>_key bigint`, khóa tự nhiên `<thực thể>_id` |
| Fact | `fct_<sự kiện>`, grain ghi trong description |
| Staging | `stg_<nguồn>__<thực thể>` (hai gạch dưới) |
| View phân tích | `v_<câu hỏi nó trả lời>` |
| Thư viện dataframe | polars |
| Ngày giờ | `timestamptz`, lưu UTC; ngày thuần dùng `date` |
| Ngày của VAERS | `RECVDATE`, `VAX_DATE`, `ONSET_DATE`, `DATEDIED` là ngày lịch (không có giờ, không có múi giờ) định dạng `MM/DD/YYYY`: chuyển thành `date`, **không** gán múi giờ và không đổi giờ. Chỉ `_ingested_at` và các cột `meta.*` là `timestamptz` UTC |
| Ngày vô lý | Ngày không parse được, `VAX_DATE` trước 2020-12-01 hoặc sau `RECVDATE`, `ONSET_DATE` trước `VAX_DATE` → NULL ở core (giá trị gốc còn ở staging), tính vào `cleaning_log.md`; khóa ngày trỏ `-1` |
| Số ngày khởi phát | `numdays` = `ONSET_DATE - VAX_DATE` tính lại từ hai ngày đã làm sạch; không dùng cột `NUMDAYS` của nguồn |
| Số tiền / độ đo | `numeric`, ghi đơn vị trong comment cột |
| Mã quốc gia | ISO 3166-1 alpha-3 (nếu topic có quốc gia) |
| Mô tả | Mọi bảng và cột có description (dbt) hoặc `COMMENT ON` (migration) |

## 4. Quy tắc NULL

Nguyên tắc: **không impute**. Thiếu giá trị thì NULL ở cột số/ngày, còn khóa ngoại tới dimension trỏ `-1` (không bao giờ NULL).

| Bảng | Không được NULL | Được NULL |
|---|---|---|
| mọi `dim_*` | `<x>_key`, khóa tự nhiên, nhãn hiển thị (dòng unknown dùng `UNKNOWN`) | cột mô tả phụ |
| `fct_report`, `fct_report_raw` | `report_key`, `vaers_id`, `received_date_key`, `vax_date_key`, `age_group_key`, `sex_key`, `state_key`, `n_symptoms` | `age_yrs` (rỗng khi nguồn không có tuổi), `numdays`, `hospdays`; các cờ `died` / `hospital` / `er_visit` / `life_threatening` / `disabled` là boolean **không NULL** (nguồn để trống nghĩa là `false`) |
| `fct_report_vaccine` | `report_key`, `vaccine_key` | `dose_series` (nguồn để trống hoặc `UNK`) |
| `fct_report_symptom` | `report_key`, `symptom_key` | — |
| `fct_report_allergen` | `report_key`, `allergen_key`, `match_type` | — |
| `report_duplicate_map` | `vaers_id`, `kept_vaers_id`, `rule_version` | — |

Cột nguồn rỗng nhiều và cách xử lý: `AGE_YRS` rỗng → `age_yrs` NULL, `age_group_key = -1` (báo cáo thiếu tuổi **vẫn ở trong fact**, chỉ bị loại khỏi phân tích tuổi/giới như bài báo); `STATE` rỗng → `state_key = -1`; `ALLERGIES` rỗng hoặc `none` / `n/a` / `no known allergies` → **không** sinh dòng trong `fct_report_allergen` (không có chất gây dị ứng khác với chưa rõ); `ALLERGIES` có chữ nhưng không map được → một dòng `UNMAPPED`.

Ràng buộc "không được NULL" phải có test `not_null` trong `schema.yml`.

## 5. Ai được ghi vào đâu

| Schema | Ghi bởi | Role |
|---|---|---|
| `raw` | chỉ ingestion, chỉ thêm | `etl_writer` (không có UPDATE/DELETE) |
| `staging`, `core`, `analytics` | chỉ dbt | `etl_writer` |
| `meta` | ingestion + quality | `etl_writer` |
| cấu trúc (DDL ngoài dbt) | chỉ migration | admin |

## 6. Điều kiện merge pull request

| PR chạm gì | Ai duyệt | Phải kèm gì |
|---|---|---|
| `db/` hoặc `transform/models/core/` | Data Architect | Dòng mới trong `decision_log.md` nếu có đánh đổi |
| Code làm sạch dữ liệu (`transform/models/`) | Data Architect | Dòng mới trong `cleaning_log.md` kèm số dòng trước/sau |
| `analysis/` hoặc kết luận thống kê | Analysis Lead | Giả định mô hình đã kiểm |
| Còn lại | Một người bất kỳ | CI xanh |

- Mọi PR đều cần CI xanh (`lint` + `pipeline`).
- Migration mới là file mới; không sửa file đã merge (CI bắt checksum lệch).
- Sửa ngoài thư mục mình sở hữu thì phải hỏi người sở hữu (bảng phân vai trong README).

## 7. Kho dùng chung

Warehouse local là bản làm việc đầy đủ 5 schema. Kho dùng chung (Neon) là **bản sao chỉ-đọc** của
`core`, `analytics`, `meta`, cập nhật bằng `make publish` (decision #29, #30).

- Chỉ Data Architect publish, và chỉ sau khi `make quality` xanh.
- Không ai được `INSERT`/`UPDATE` trực tiếp trên kho chung: mỗi lần publish thay toàn bộ ba schema.
- `raw` và `staging` không có trên kho chung. Truy vết một dòng `core` về `raw` phải làm ở local.
- Cách kết nối và vận hành kho chung: [kho_du_lieu.md](kho_du_lieu.md).
- Số liệu trong báo cáo phải lấy từ kho chung (hoặc từ local đã publish cùng một lần chạy), để cả
  nhóm trích cùng một con số.

## 8. Hai đường lấy dữ liệu

- `live` là đường chính; mọi lô live lưu bản gốc từng trang vào `data/raw/<source>/<ngày>/<batch_id>/` trước khi parse.
- `mock` chỉ phát lại bản gốc đó qua `mock_server`; không sinh dữ liệu giả, không sửa bản gốc (sha256 kiểm khi nạp).
- Mỗi lô ghi `source_mode` vào `meta.ingestion_batch`. Lô live và lô mock của cùng snapshot phải trùng số dòng và tập `_row_hash` (`make mock-check`).
