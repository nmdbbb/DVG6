# Data contract

> Bản nháp do khung repo sinh ra. Data Architect chốt sau buổi chọn topic; sau khi chốt, sửa file này phải báo cả nhóm.

## 1. Bảng core và grain

| Bảng | Grain |
|---|---|
| `core.dim_entity` | Một dòng cho mỗi thực thể (`entity_id`), cộng dòng unknown `entity_key = -1` |
| `core.fct_main` | Một dòng cho mỗi sự kiện đo (`record_id`) |

Thêm bảng core mới phải ghi grain vào đây **trước** khi viết model.

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
| Số tiền / độ đo | `numeric`, ghi đơn vị trong comment cột |
| Mã quốc gia | ISO 3166-1 alpha-3 (nếu topic có quốc gia) |
| Mô tả | Mọi bảng và cột có description (dbt) hoặc `COMMENT ON` (migration) |

## 4. Quy tắc NULL

| Bảng | Không được NULL | Được NULL |
|---|---|---|
| `dim_entity` | `entity_key`, `entity_id` | `entity_name`, `category` (chỉ dòng unknown) |
| `fct_main` | `record_id`, `entity_key`, `event_date` | `measure_value` (nguồn để trống; không impute) |

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

## 7. Hai đường lấy dữ liệu

- `live` là đường chính; mọi lô live lưu bản gốc từng trang vào `data/raw/<source>/<ngày>/<batch_id>/` trước khi parse.
- `mock` chỉ phát lại bản gốc đó qua `mock_server`; không sinh dữ liệu giả, không sửa bản gốc (sha256 kiểm khi nạp).
- Mỗi lô ghi `source_mode` vào `meta.ingestion_batch`. Lô live và lô mock của cùng snapshot phải trùng số dòng và tập `_row_hash` (`make mock-check`).
