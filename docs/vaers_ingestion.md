# Nạp VAERS — Crawl A

Ba connector `vaers_data`, `vaers_symptoms`, `vaers_vax` đọc chung một ZIP,
nhưng mỗi connector ghi một bảng, một lô và một thư mục snapshot riêng.
Giữ nguyên framework một connector → một bảng; không sửa loader hay mock server.

## Kiểm tra local, không cần Docker

Chạy từ thư mục repo, với Python và thư viện `httpx` đã cài:

```powershell
python -m ingestion.sources.vaers --limit 10
python -m pytest ingestion/tests -q
```

Preview kiểm SHA-256 rồi parse tối đa 10 bản ghi mỗi CSV, không hiển thị nội dung
báo cáo, không kết nối database và không tạo snapshot thật. Có thể tăng `--limit`.

`ingestion/sources/vaers_landing.json` đăng ký ZIP, năm, SHA-256 và encoding
Windows-1252 (`cp1252`). Không đoán hoặc thay thế ký tự lỗi khi decode. Muốn dùng
file khác, kiểm tra bằng `ingestion.inspect_vaers`, thêm nhật ký landing rồi cập nhật
manifest; có thể chọn manifest riêng bằng biến môi trường `VAERS_MANIFEST`.
Không thay checksum chỉ để bỏ qua lỗi kiểm tra file.

## Nạp thử khi PostgreSQL và mock server đang chạy

Sau khi migration `006` đã được áp dụng:

```powershell
docker compose run --rm etl python -m ingestion.cli run --source vaers_data --limit 100
docker compose run --rm etl python -m ingestion.cli run --source vaers_symptoms --limit 100
docker compose run --rm etl python -m ingestion.cli run --source vaers_vax --limit 100
```

Chạy lại cùng lệnh: `new_rows=0` nếu lần trước thành công và không có dữ liệu thay đổi.
Bỏ `--limit 100` khi cần nạp toàn bộ. Không hỗ trợ `--since`: raw luôn giữ nguyên
snapshot của năm đã đăng ký, không lọc COVID19 hoặc ngày trong connector.

Loader có sẵn lưu trang bytes CSV trước `parse()` vào
`data/raw/<source>/<ngày>/<batch_id>/page_NNNNN.bin` và `manifest.json`.
Đuôi `.bin` do framework hiện tại chưa đặt đuôi riêng cho CSV; content-type lưu
`text/csv; charset=cp1252`, nội dung vẫn là CSV. Mỗi trang có header và tối đa
1000 bản ghi hoàn chỉnh, không cắt giữa ô nhiều dòng. Các bytes của dòng nguồn
được giữ nguyên; header lặp lại để từng trang đọc độc lập.

Các cột CSV giữ nguyên chữ hoa (SQL cần dùng dấu ngoặc kép, ví dụ `"VAERS_ID"`).
Khóa chống nạp lại là MD5 của dict bản ghi dạng JSON sắp khóa, không phải MD5
bytes của dòng CSV. `VAERS_ID` không unique; raw chưa khử trùng lặp nghiệp vụ.

## Phối hợp Crawl B

Mock HTML hiện có hỗ trợ cả ba tên nguồn, không cần thêm route.
Seed đọc snapshot CSV bằng connector `parse()`; mock phát HTML; connector đọc HTML
bằng parser chung. Sau khi có snapshot live, nạp mock bằng:

```powershell
docker compose run --rm etl python -m ingestion.cli run --source vaers_data --endpoint mock
docker compose run --rm etl python -m scripts.compare_batches --source vaers_data
```

Lặp lại với `vaers_symptoms`, `vaers_vax`. So khớp phải dùng cùng snapshot và
cùng tập bản ghi; không thêm `--limit` khác với lần live.

CI không có ZIP tải tay nên pipeline CI đặt `SOURCE=source_demo`; test VAERS dùng
ZIP nhỏ tự tạo, không phụ thuộc dữ liệu local. Nhánh này vẫn giữ nguồn demo cho
dbt/quality hiện tại; chuyển transform sang VAERS là phần việc tiếp theo của nhóm.

## Kết quả kiểm tra local ngày 2026-10-16

- 19 test ingestion đạt (gồm source_demo và VAERS).
- ZIP đăng ký được đọc toàn bộ: DATA 768704 bản ghi, SYMPTOMS 1030201,
  VAX 813432. Đây là số bản ghi nguồn trước khi chống nạp lại và lọc COVID19.
- Đã kiểm giá trị có dấu phẩy, ngoặc kép, xuống dòng, ký tự Windows-1252,
  giữ nguyên bytes khi chia trang, checksum sai và hash khi phát lại HTML.
- Chưa kiểm trên PostgreSQL hay HTTP mock server trong lượt này vì Docker đang tắt.
- Chưa chạy Ruff/Black vì Python local chưa có hai công cụ này.
