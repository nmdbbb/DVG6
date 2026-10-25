# Cleaning log

Mỗi phép biến đổi trong `transform/` là một dòng. **Không có dòng ở đây thì bảng sạch không được merge** (cổng do Data Architect gác).

Số liệu dưới đây đo trên `source_demo` (5 000 bản ghi, seed 20261005). Khi thay bằng nguồn thật ở M5, các dòng #1–#7 được thay bằng dòng của nguồn thật.

| # | Bảng | Phép biến đổi | Dòng trước | Dòng sau | Lý do |
|---|------|---------------|-----------|---------|-------|
| 1 | `stg_source_demo__records` | Chỉ lấy dòng raw thuộc lô `status = 'success'` | 5 000 | 5 000 | Lô fail/đang chạy có thể ghi dở; raw giữ nguyên làm bằng chứng nhưng không đi tiếp |
| 2 | `stg_source_demo__records` | `trim` + `upper` cho `entity_code`, `upper` cho `category`, chuỗi rỗng → NULL, ép kiểu `date` / `numeric(14,4)` | 5 000 | 5 000 | 501 mã thực thể và 505 nhóm bị viết thường/thừa khoảng trắng; không chuẩn hóa thì join dimension bị lệch |
| 3 | `fct_main` | Bỏ dòng thiếu `record_id` | 5 000 | 4 942 | Không có khóa grain thì không định nghĩa được sự kiện; chiếm 1,16% |
| 4 | `fct_main` | Khử trùng lặp theo `record_id`, giữ bản nạp sau cùng (`ingested_at`), hòa thì theo `row_hash` | 4 942 | 4 926 | 16 cặp trùng khóa, khác nhau chỉ ở khoảng trắng của tên → cùng một sự kiện |
| 5 | `fct_main` | Sự kiện không có mã thực thể trỏ về `entity_key = -1` (unknown) thay vì bị loại khi join | 4 926 | 4 926 | 24 dòng (0,49%); giữ để tổng độ đo không âm thầm hụt; quality cảnh báo khi > 1% |
| 6 | `dim_entity` | Tên và nhóm của mỗi `entity_id` lấy giá trị xuất hiện nhiều nhất (`mode()`) | 20 mã | 20 + 1 unknown | Một mã có thể mang nhiều biến thể tên; chọn giá trị phổ biến nhất là quy tắc tất định, dễ giải thích |
| 7 | `fct_main` | `measure_value` rỗng giữ NULL, không impute; ngoại lai (> TB + 4 SD) giữ nguyên | 87 NULL · 9 ngoại lai | không đổi | NULL chiếm 1,77% (< ngưỡng 5%); impute sẽ bịa số. Ngoại lai chỉ cảnh báo, quyết định cắt hay giữ để Analysis Lead chốt khi có dữ liệu thật |
| 8 | `stg_vaers__data`, `stg_vaers__vax` | Chỉ lấy dòng raw thuộc lô `status = 'success'`, đổi tên cột `snake_case`, `trim` + `upper` cho mã phân loại, chuỗi rỗng → NULL, ép kiểu ngày `MM/DD/YYYY` sang `date` và ép kiểu số | 768 704 (`vaers_data`) · 811 756 (`vaers_vax`) | 768 704 (`stg_vaers__data`) · 811 756 (`stg_vaers__vax`) | Chuẩn hóa kiểu dữ liệu và khoảng trắng ở staging nhưng không lọc bỏ dòng và không cắt ngoại lai (xử lý ở core) |
| 9 | `stg_vaers__symptoms` | Unpivot 5 cặp cột `SYMPTOM1..SYMPTOM5` và `SYMPTOMVERSION1..5` thành từng dòng `(vaers_id, symptom_slot, symptom_name)`, bỏ ô triệu chứng rỗng | 1 030 201 dòng raw (3 263 884 ô triệu chứng khác rỗng) | 3 263 884 dòng triệu chứng | Đưa dữ liệu triệu chứng từ dạng rộng (5 cột) về dạng dọc; đối chiếu khớp 100% số ô khác rỗng qua check `vaers_symptoms_unpivot_reconciliation` |
| 10 | `stg_openfda__substances` | Lấy dòng thuộc lô `status = 'success'`, tách mảng JSON `substance_name`, `trim` + `upper`, bỏ rỗng và khử trùng lặp theo `substance_name` | 26 000 nhãn thuốc | 3 883 hoạt chất | Nhiều nhãn thuốc chứa cùng một hoạt chất; khử trùng lặp để tạo từ điển hoạt chất chuẩn phục vụ đối chiếu cột `ALLERGIES` |