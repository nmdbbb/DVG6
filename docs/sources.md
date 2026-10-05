# Nguồn dữ liệu

Mỗi nguồn một mục. Người viết connector giữ mục của nguồn mình. Thông tin mô tả (url, license, tần suất, owner) cũng nằm trong `describe()` của connector và được ghi vào `meta.source`, nên dashboard hiện đúng nội dung này.

## Mẫu cho nguồn mới

| Thuộc tính | Giá trị |
|---|---|
| `source_name` | |
| Connector | `ingestion/sources/<tên>.py` |
| Bảng raw | `raw.<tên>_<thực thể>` (migration số …) |
| URL / API | |
| Giấy phép | |
| Tần suất cập nhật | |
| Cách lấy (live) | API chính thức / file tải về / scrape (phải tôn trọng `robots.txt`, dùng `http_client.get()`) |
| Đường mock | `mock_format = "json"` (API: override `render_api_page()` đúng hình dạng response) hoặc `"html"` (trang web) |
| Khóa định danh bản ghi | cột nào tạo `_row_hash` |
| Phạm vi thời gian | |
| Rủi ro đã biết | |

Data dictionary: bảng cột | kiểu ở nguồn | ý nghĩa | ví dụ.

---

## source_demo (giả, chỉ dùng cho M1–M4)

| Thuộc tính | Giá trị |
|---|---|
| `source_name` | `source_demo` |
| Connector | [`ingestion/sources/source_demo.py`](../ingestion/sources/source_demo.py) |
| Bảng raw | `raw.source_demo_records` (migration `003`) |
| URL / API | không có — giả lập API JSON phân trang trong process, `random.Random(seed=20261005)` |
| Hình dạng response | `{"count", "page", "page_size", "results": [...]}`, 500 bản ghi/trang |
| Đường mock | `mock_format = "json"`, `mock_page_size = 500` → 10 request tới `/api/source_demo` |
| Giấy phép | nội bộ nhóm |
| Tần suất | chạy theo yêu cầu |
| Khóa định danh | md5 của toàn bộ bản ghi (mặc định của `Connector.row_hash`) |
| Phạm vi | 5 000 sự kiện, 2020-01-01 → 2025-12-31, 20 thực thể, 4 nhóm |

| Cột | Kiểu ở nguồn | Ý nghĩa | Ví dụ |
|---|---|---|---|
| `record_id` | chuỗi | mã sự kiện; ~1% rỗng | `R000042` |
| `entity_code` | chuỗi | mã thực thể; ~10% viết thường/thừa khoảng trắng, ~0,5% rỗng | `E007`, `  e007 ` |
| `entity_name` | chuỗi | tên thực thể | `Entity 07` |
| `category` | chuỗi | nhóm A–D; ~10% viết thường | `C` |
| `event_date` | chuỗi ISO | ngày sự kiện | `2023-05-14` |
| `measure_value` | chuỗi số | độ đo log-normal; ~2% rỗng, ~0,3% ngoại lai ×20 | `87.31` |

Dữ liệu cố tình bẩn để mọi nhánh của transform và quality đều chạy. Chạy lại cùng tham số cho đúng các bản ghi cũ, nên lô thứ hai ghi 0 dòng mới.
