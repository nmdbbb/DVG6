# Nạp VAERS — Crawl A

Ba connector `vaers_data`, `vaers_symptoms`, `vaers_vax` đọc chung một ZIP,
nhưng mỗi connector ghi một bảng, một lô và một thư mục snapshot riêng.
Giữ nguyên framework một connector → một bảng; không sửa loader hay mock server.

## Kiểm tra local, không cần Docker

### Chọn năm 2021–2026

Manifest `ingestion/sources/vaers_landing.json` đăng ký riêng đường dẫn và SHA-256
cho sáu ZIP 2021–2026. Mặc định vẫn là 2021. Ví dụ preview năm 2022:

```powershell
python -m ingestion.sources.vaers --year 2022 --limit 10
```

Lặp lại với `--year 2023` đến `--year 2026`. Không ghi database khi preview.
Nếu cần nạp PostgreSQL local theo luồng cũ, truyền năm vào container:

```powershell
docker compose run --rm --no-deps -e VAERS_YEAR=2022 etl python -m ingestion.cli run --source vaers_data --endpoint live --limit 100
```

Lặp với `vaers_symptoms` và `vaers_vax`. Ba bảng raw hiện có nhận thêm bản ghi,
không tạo bảng theo năm; đây không phải thao tác làm sạch. Không thêm cột năm giả
vào bản ghi nguồn hoặc thay đổi cách tính hash cũ. `_source_name` vẫn là tên
connector; nguồn ZIP/năm nằm trong URL trang của manifest snapshot và mô tả nguồn
tại thời điểm chạy. Chưa có cột năm file riêng trong raw để truy vấn độc lập.

**Mock chỉ phát snapshot hoàn chỉnh mới nhất của mỗi connector**, không gộp các
lần nạp năm khác nhau. Nếu chuyển năm, lần live/mock đối chiếu phải dùng đúng
snapshot đó; biến `VAERS_YEAR` không chọn lại một snapshot mock cũ.

Theo cách bàn giao của nhóm, các ZIP gốc cần được upload riêng lên Release
`landing`, với tên `vaers__2026-10-15__2022VAERSData.zip` (tương tự 2023–2026).
Checksum nằm trong nhật ký nguồn. Các file mới dùng thư mục cũ theo lựa chọn của
người dùng; `2026-10-15` trong đường dẫn không xác nhận ngày tải thực tế.
Năm 2026 chưa phải dữ liệu trọn năm tại ngày đăng ký 2026-10-26.
Việc hỗ trợ đọc thêm năm không tự thay đổi phạm vi nghiên cứu của nhóm.

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

## Phục hồi sau lô lỗi — bàn giao cho Transform

Mỗi lần chạy tạo một `batch_id` mới. Loader commit từng khối, nên một lô bị lỗi
hoặc bị dừng có thể đã ghi nhiều dòng vào raw. `_batch_id` của dòng raw chỉ lô đầu
tiên ghi dòng đó. Khi chạy lại, hash trùng không được chèn thêm và `_batch_id`
không đổi, nhưng `meta.ingestion_batch_row` vẫn ghi nhận hash trong lô mới.

Vì vậy, lô gốc `failed` không có nghĩa mọi dòng của lô đó đều sai. Nếu một lô sau
hoàn thành với `success` và có cùng hash, dòng đã được xác nhận qua lần nạp thành
công. Giữ nguyên trạng thái lỗi lịch sử và dữ liệu raw; không đổi lô cũ sang
`success`, không xóa bảng và không UPDATE `_batch_id` để che lịch sử lỗi.

**Yêu cầu cho staging VAERS:** nhận dòng khi hash đã xuất hiện trong ít nhất một
lô `success` của cùng `source_name`. Không chỉ JOIN qua `raw._batch_id` rồi lọc
`status = 'success'`: cách đó bỏ sót dữ liệu hợp lệ sau lần chạy lại. Dùng `EXISTS`
để mỗi dòng raw chỉ xuất hiện một lần dù nhiều lô thành công đã đọc cùng hash.

SQL tham khảo cho model triệu chứng (áp dụng trước unpivot/làm sạch):

```sql
select r.*
from raw.vaers_symptoms r
where exists (
    select 1
    from meta.ingestion_batch_row br
    join meta.ingestion_batch b on b.batch_id = br.batch_id
    where br.row_hash = r._row_hash
      and b.source_name = r._source_name
      and b.status = 'success'
);
```

Áp dụng cùng điều kiện cho `raw.vaers_data` và `raw.vaers_vax`. Không chỉ so hash
mà bỏ nguồn, vì các nguồn khác nhau có thể có cùng hash. Điều kiện này xác nhận
đã nạp thành công, không thay thế kiểm tra chất lượng hay khử trùng lặp nghiệp vụ.

**Trường hợp đã xác nhận ngày 2026-10-16, theo kết quả SQL người dùng cung cấp:**

- `raw.vaers_symptoms` có 1030201 dòng: 874900 dòng gắn lô gốc `failed`,
  155301 dòng gắn lô gốc `success`.
- Kiểm tra hash trong lô thành công của nguồn `vaers_symptoms` trả về đủ
  1030201 dòng. Không cần nạp lại chỉ để đổi trạng thái lô gốc.
- Đây là kết quả kiểm tra database, chưa chứng minh model staging đã áp dụng
  đúng điều kiện. Người làm Transform cần triển khai và kiểm tra số dòng trước
  các phép lọc/unpivot; không coi ghi chú này là bản sửa logic staging đã hoàn tất.
- Lô còn `running` cần được người vận hành kiểm tra có tiến trình đang chạy hay
  đã bị gián đoạn; không tự đổi trạng thái khi chưa xác minh.

Nếu số dòng được xác nhận nhỏ hơn số dòng raw, kiểm tra các lô lỗi và nhật ký
hash trước khi quyết định chạy lại. Không nhận dòng chỉ xuất hiện trong lô lỗi.

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
