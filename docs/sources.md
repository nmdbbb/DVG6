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

## source_demo (giả, chỉ dùng cho M1–M4; gỡ khỏi registry khi M5 xong)

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

---

## vaers (nguồn chính, M5)

| Thuộc tính | Giá trị |
|---|---|
| `source_name` | `vaers_data`, `vaers_symptoms`, `vaers_vax` (mỗi CSV một connector) |
| Connector | `ingestion/sources/vaers.py` (Source & Crawler A) |
| Bảng raw | `raw.vaers_data`, `raw.vaers_symptoms`, `raw.vaers_vax` (migration `006`) |
| URL | https://vaers.hhs.gov/data/datasets.html |
| Giấy phép | Dữ liệu công cộng của chính phủ Mỹ (CDC/FDA/HHS). Không có điều khoản hạn chế dùng lại; phải kèm cảnh báo diễn giải của VAERS Data Use Guide. |
| Tần suất cập nhật | Hàng tuần; dữ liệu đã khử định danh xuất hiện sau 4–6 tuần |
| Cách lấy (live) | **Tải tay một lần** — xem mục "Tại sao không crawl được" bên dưới |
| Đường mock | `mock_format = "html"` — mock_server phát lại snapshot đã lưu |
| Khóa định danh bản ghi | md5 của toàn bộ bản ghi dạng JSON sắp khóa, giữ nguyên giá trị chuỗi và khoảng trắng; không phải hash bytes CSV |
| Phạm vi | Báo cáo nhận trong 2021, `VAX_TYPE = 'COVID19'` |
| Rủi ro đã biết | Báo cáo thụ động: trùng lặp ~29%, thiếu giá trị, sai chính tả, không có mẫu số |

### Tại sao không crawl được, và nhóm làm thế nào

Trang tải của VAERS (`/eSubDownload/index.jsp?fn=2021VAERSData.zip`) trả về một form có **CAPTCHA** (`<input name="verificationCode">`). Đây là biện pháp chống tải hàng loạt của CDC/FDA, nên **không được vượt qua bằng script** — vi phạm nguyên tắc tôn trọng nguồn trong [data_contract.md](data_contract.md).

Quy trình nhóm dùng:

0. **Người mới vào nhóm: chỉ cần `make landing-fetch`** — file đã có sẵn trên GitHub Release,
   không phải vào trang CDC. Các bước dưới chỉ dành cho người tải tay lần đầu.
1. **Một người tải tay một lần**, chọn file năm cần, nhập mã xác thực.
2. Đặt file ZIP vào `data/landing/vaers/<ngày>/2021VAERSData.zip` (thư mục `data/` không commit).
3. `make landing-register SOURCE=vaers` ghi tên file, kích thước, **sha256** và ngày tải vào
   [sources_landing.md](sources_landing.md) — đây là sổ đăng ký của cả nhóm.
4. `make landing-upload SOURCE=vaers` đẩy file lên GitHub Release để 6 người còn lại chỉ cần
   `make landing-fetch`, không ai phải đụng CAPTCHA của CDC nữa.
5. `python -m ingestion.inspect_vaers <đường-dẫn-ZIP>` ghi đường dẫn, checksum và encoding vào
   `ingestion/sources/vaers_landing.json` — manifest mà ba connector đọc.
6. Chạy riêng từng connector: `make ingest SOURCE=vaers_data`, `SOURCE=vaers_symptoms`,
   `SOURCE=vaers_vax`. Mỗi connector tự kiểm sha256 trước khi đọc CSV. Cách chạy không cần make
   và cách xem trước dữ liệu: [vaers_ingestion.md](vaers_ingestion.md).

> **Đang có hai sổ đăng ký cho cùng một file:** `sources_landing.md` (bước 3, cho cả nhóm) và
> `vaers_landing.json` (bước 5, cho connector). Hai chỗ ghi cùng một sha256 nên có thể lệch nhau.
> Cần gộp làm một — xem issue về việc này.


Bản ZIP là **bản gốc bất biến** của nguồn: connector lưu từng khối CSV thành trang trong `data/raw/vaers/<ngày>/<batch_id>/`, nên mock_server phát lại được và `make mock-check` vẫn khớp `_row_hash` như mọi nguồn khác.

Vì bước 1 là thao tác tay, `make reset && make all` trên máy trống **cần file ZIP có sẵn trong landing**. Runbook phải ghi rõ điều này.

### Ba file CSV trong ZIP

`2021VAERSDATA.csv` — một dòng cho mỗi báo cáo, khóa `VAERS_ID`:

| Cột | Kiểu ở nguồn | Ý nghĩa |
|---|---|---|
| `VAERS_ID` | số | Mã báo cáo, khóa tự nhiên |
| `RECVDATE` | chuỗi ngày | Ngày VAERS nhận báo cáo |
| `STATE` | chuỗi | Mã bang 2 chữ cái; rỗng nhiều |
| `AGE_YRS` | số thực | Tuổi (năm); rỗng ở ~7% báo cáo |
| `SEX` | chuỗi | `M`, `F`, `U` (không rõ) |
| `VAX_DATE` | chuỗi ngày | Ngày tiêm |
| `ONSET_DATE`, `NUMDAYS` | ngày, số | Ngày khởi phát và số ngày sau tiêm |
| `DIED`, `L_THREAT`, `HOSPITAL`, `DISABLE`, `ER_VISIT`, `BIRTH_DEFECT` | `Y` hoặc rỗng | Mức độ nghiêm trọng |
| `ALLERGIES` | văn bản tự do | Tiền sử dị ứng — **nguồn sai chính tả chính** |
| `CUR_ILL`, `HISTORY`, `OTHER_MEDS` | văn bản tự do | Bệnh hiện tại, tiền sử, thuốc đang dùng |
| `SYMPTOM_TEXT` | văn bản tự do dài | Mô tả tự do của người báo cáo |

`2021VAERSVAX.csv` — một dòng cho mỗi vắc xin trong một báo cáo (nhiều dòng cùng `VAERS_ID`): `VAX_TYPE`, `VAX_MANU`, `VAX_LOT`, `VAX_DOSE_SERIES`, `VAX_ROUTE`, `VAX_SITE`, `VAX_NAME`.

`2021VAERSSYMPTOMS.csv` — tối đa **5 triệu chứng mỗi dòng**, một báo cáo có thể có nhiều dòng: `VAERS_ID`, `SYMPTOM1`…`SYMPTOM5`, `SYMPTOMVERSION1`…`SYMPTOMVERSION5`. Triệu chứng là thuật ngữ MedDRA Preferred Term. Tầng staging phải **unpivot** 5 cột này thành một dòng cho mỗi (báo cáo, triệu chứng) — giới hạn 5 cột này chính là lý do một người nộp nhiều form, sinh ra trùng lặp.

---

## openfda (nguồn phụ, M5)

| Thuộc tính | Giá trị |
|---|---|
| `source_name` | `openfda` |
| Connector | `ingestion/sources/openfda.py` (Crawler B & Mock server) |
| Bảng raw | `raw.openfda_substances` (migration `006`) |
| URL / API | `https://api.fda.gov/drug/label.json` |
| Giấy phép | https://open.fda.gov/license/ — public domain (CC0), có kèm disclaimer bắt buộc hiển thị |
| Tần suất cập nhật | Hàng tuần (`meta.last_updated` trong mỗi response) |
| Cách lấy (live) | HTTP API thật, phân trang bằng `limit` + `skip`, dùng `http_client.get()` |
| Giới hạn tốc độ | 240 request/phút và 1 000 request/ngày khi không có API key; trả `429` khi vượt |
| Đường mock | `mock_format = "json"`, override `render_api_page()` theo hình dạng `{"meta": {...}, "results": [...]}` |
| Khóa định danh bản ghi | `spl_id` của nhãn thuốc |
| Rủi ro đã biết | `skip` tối đa 25 000; dữ liệu là nhãn thuốc, không phải vắc xin — chỉ dùng làm từ điển hoạt chất |

**Dùng để làm gì.** Cột `ALLERGIES` của VAERS là văn bản tự do, và bài báo đo được ~14% mục penicillin viết sai chính tả (`penecellin`, `penecillin`, `penecilin`). Nhóm lấy danh sách **tên hoạt chất chuẩn** (`openfda.substance_name`, kèm `rxcui`) từ openFDA làm từ điển, rồi so khớp mờ với văn bản tự do để dựng `dim_allergen`. Đây là phần "tích hợp dữ liệu từ nhiều nguồn" của đề bài, và nó phục vụ trực tiếp câu hỏi Q3.

Mỗi lần chuẩn hóa phải ghi lại: bao nhiêu chuỗi khớp chính xác, bao nhiêu khớp mờ, bao nhiêu không khớp (vào `dim_allergen` dưới nhãn `UNMAPPED`, **không** vứt đi).
