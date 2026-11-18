# Hợp đồng phân tích và dashboard

## Mục tiêu

Dashboard hỗ trợ khám phá và ra quyết định dựa trên các báo cáo VAERS về vắc xin COVID-19. Dashboard phải cho thấy triệu chứng và outcome được báo cáo thay đổi theo thời gian ra sao, cho phép so sánh các nhóm, đồng thời lần theo được batch và dữ liệu đã góp phần tạo ra thay đổi đó.

Đây là phân tích **báo cáo gửi tới VAERS**. Số lượng và tỷ lệ không phải tỷ lệ mắc bệnh, nguy cơ trên người tiêm, bằng chứng nhân quả hay chẩn đoán lâm sàng. Một báo cáo có thể nêu nhiều triệu chứng và nhiều vắc xin.

## Phân vai notebook

Hai thư mục notebook hiện có các vai trò sau:

| Lớp | Notebook hiện tại | Vai trò với dashboard/model |
|---|---|---|
| `analysis/notebooks/frontend/` | A0 tổng quan, A1 tần suất, A9 thời gian khởi phát, A10 outcome, A11 đồng xuất hiện, A12 so sánh nhóm | Tài liệu tham chiếu cho câu hỏi biểu đồ, trục, mẫu số, bộ lọc, nhãn và cách diễn giải. Biểu đồ sản phẩm được triển khai ở web frontend và lấy dữ liệu qua API/analytics contract. |
| `analysis/notebooks/backend/` | A2 hồ sơ tuổi/giới, A3 kiểm định độc lập, A4 phân cụm, A5 luật kết hợp, A6 SOM, A7 liên kết, A8 phân bố tuổi | Phân tích khám phá đặc trưng và mối liên hệ. Kết quả đã được rà soát có thể trở thành tín hiệu ứng viên cho mô hình hỗ trợ, sau khi xác định và kiểm định mô hình. |

Notebook là artifact phân tích có thể tái tạo, không phải thành phần chạy bên trong dashboard. Hiện các workflow đọc bảng core rồi lưu CSV/PNG trên máy; production không được chạy notebook hoặc đọc các file này. Dữ liệu cho dashboard phải được cung cấp qua model `analytics` có mô tả và API chỉ đọc.

Notebook backend chưa tự tạo thành một mô hình dự báo. A3 kiểm định phụ thuộc tổng thể giữa biến phân loại và hồ sơ triệu chứng; A5 đo luật đồng xuất hiện trong báo cáo; A4/A6 mô tả cấu trúc của ma trận đặc trưng; A7 mô tả liên kết theo báo cáo. Những kết quả đó giúp đề xuất giả thuyết hoặc feature. Mỗi mô hình cần nêu rõ target, horizon, quần thể áp dụng, cách validation, metrics hiệu năng/calibration, độ bất định và giới hạn. Association hay clustering riêng lẻ không phải dự báo và không được trình bày như chẩn đoán.

## Ngữ nghĩa thời gian

Phân biệt hai loại thời gian:

1. **Thời điểm nhận báo cáo:** `core.fct_report.recvdate` (hoặc `received_date_key`) là ngày VAERS nhận báo cáo. Dùng trường này cho xu hướng số báo cáo theo thời gian. Nó không cho biết ngày triệu chứng bắt đầu.
2. **Thời điểm nạp dữ liệu:** `meta.ingestion_batch.started_at` / `finished_at` cho biết dự án lấy batch từ nguồn khi nào. Dùng cho độ mới dữ liệu, hoạt động pipeline và giải thích thời điểm warehouse thay đổi.

`core.fct_report.vax_date`, `onset_date`, `numdays` dùng để phân tích khoảng từ tiêm đến khởi phát. Đây là một phép đo thời gian khác, không thay thế `recvdate` trong biểu đồ thời điểm gửi báo cáo. Với báo cáo có nhiều triệu chứng, VAERS không cho ngày khởi phát riêng của từng triệu chứng.

## Hành vi dashboard cần có

### 1. Tổng quan tập trung vào thời gian

- Mặc định hiển thị số báo cáo theo tháng nhận; chỉ cho chọn ngày/tuần khi cỡ mẫu đủ để đọc.
- Trên mỗi biểu đồ, ghi khoảng ngày đang chọn, khoảng dùng để so sánh, thời điểm nạp thành công gần nhất (`as_of`) và số báo cáo làm mẫu.
- Khi phù hợp, hiển thị cả số báo cáo tuyệt đối lẫn phần trăm trong nhóm; định nghĩa mẫu số trong tiêu đề, tooltip hoặc subtitle.
- So sánh với khoảng liền trước có cùng độ dài và có thể thêm cùng kỳ năm trước. Hiện delta tuyệt đối và delta phần trăm. Nếu kỳ gốc bằng 0, chỉ hiện delta tuyệt đối và đánh dấu phần trăm không xác định.
- Dùng bộ lọc nhất quán: triệu chứng, sản phẩm/hãng, nhóm tuổi, giới, khoảng ngày/năm nhận và outcome cấp báo cáo. Giá trị `UNKNOWN`/không rõ phải là nhóm có thể chọn.
- Đánh dấu kỳ hiện tại chưa đầy đủ và trạng thái batch thành công/thất bại. Không so kỳ chưa đủ với kỳ đủ mà không ghi rõ.

### 2. Giải thích mỗi thay đổi quan sát được

Từ mỗi chỉ số hoặc biểu đồ phải mở được mục “Vì sao số liệu thay đổi?”. Mục này giải thích thay đổi của **chỉ số báo cáo**, không khẳng định nguyên nhân y khoa.

Chi tiết cần có:

- metric, bộ lọc/nhóm, hai khoảng thời gian, giá trị cũ/mới, delta tuyệt đối và delta phần trăm nếu xác định được;
- các báo cáo đóng góp, tách thành báo cáo mới được quan sát, nội dung báo cáo được cập nhật, thay đổi do khử trùng/điều kiện hợp lệ và thay đổi do transform/quality rule;
- với từng đóng góp: `VAERS_ID`/`report_key` nếu chính sách truy cập cho phép, triệu chứng/sản phẩm/nhóm bị ảnh hưởng, nguồn, `batch_id`, `source_mode` (`live`/`mock`), thời gian/trạng thái batch và raw row hash/version liên quan;
- liên kết từ đóng góp tới chi tiết batch, và từ giải thích tới transform/quality run đã dùng để publish kết quả hiện tại.

Phân rã đóng góp phải cộng lại bằng delta hiển thị. Nếu một báo cáo được sửa, giao diện chỉ rõ trường nào đổi (ví dụ tập triệu chứng hoặc sản phẩm) và metric bị tác động thế nào. Nếu không đối soát được toàn bộ contributors, phải ghi giải thích chưa đầy đủ thay vì ngụ ý danh sách đã giải thích hết thay đổi.

### 3. Góc nhìn hỗ trợ mô hình

- Hiển thị tín hiệu từ notebook backend tách biệt với xu hướng mô tả: thước đo liên hệ, cỡ mẫu, độ bất định/kết quả kiểm định, cửa sổ phân tích, định nghĩa feature và phiên bản phân tích/mô hình.
- Cho xem lineage của feature và biết giá trị đến từ trường nguồn, quy tắc cleaning hay phép phân tích dẫn xuất.
- Không xếp hạng sản phẩm an toàn/nguy hiểm bằng số báo cáo đơn thuần. Không trình bày liên hệ giữa triệu chứng như nhân quả hoặc lời khuyên điều trị cá nhân.

## Theo dõi mô hình và quyết định huấn luyện lại

Dashboard cần có một khu vực dành cho mô hình dự báo, tách rõ dự báo với thống kê mô tả VAERS. Mục đích là giúp người dùng theo dõi mô hình đang hoạt động, kiểm tra khi dữ liệu thay đổi và đánh giá một phiên bản huấn luyện mới trước khi thay thế. Đây là hỗ trợ phân tích; không đưa ra chẩn đoán hay quyết định điều trị.

### Nội dung hiển thị

- **Prediction:** kết quả dự đoán cho từng kỳ hoặc nhóm được chọn, gồm nhãn/lớp dự đoán, xác suất (nếu mô hình có xác suất), ngưỡng phân loại, model version, thời điểm dự đoán và phạm vi dữ liệu đầu vào. Cho phép xem tổng hợp theo thời gian và drill-down tới bản ghi nếu quyền truy cập cho phép.
- **Thực trạng (observed outcome):** khi nhãn thực tế đã có và đủ trưởng thành, đặt cạnh dự đoán trên cùng cohort và cùng định nghĩa thời gian. Ghi rõ số nhãn đã quan sát, số còn thiếu/chưa đủ thời gian theo dõi và thời điểm chốt nhãn. Không coi symptom được ghi trong một báo cáo là kết quả đã được xác minh lâm sàng.
- **Chất lượng dự báo:** chọn metric phù hợp với target và mất cân bằng lớp, chẳng hạn PR-AUC, ROC-AUC, precision/recall, F1, confusion matrix; thêm Brier score hoặc biểu đồ calibration khi xác suất có ý nghĩa. Luôn hiện cỡ mẫu, khoảng thời gian, ngưỡng và phiên bản model. Không tính metric trên dự đoán chưa có nhãn thực tế.
- **Distribution shift:** theo dõi riêng thay đổi phân phối feature đầu vào và thay đổi hiệu năng khi nhãn thực tế đã có. Có thể dùng PSI hoặc Jensen–Shannon cho phân phối phân loại/nhóm, KS hoặc Wasserstein cho biến liên tục, và so sánh tỷ lệ thiếu/UNKNOWN. Với performance shift, theo dõi metric dự báo theo các cửa sổ thời gian. Hiện baseline/reference window, current window, cỡ mẫu và giá trị metric; ngưỡng cảnh báo phải được hiệu chỉnh theo dữ liệu và kiểm định, không mặc định một ngưỡng chung là bằng chứng mô hình hỏng.
- **Bản ghi liên quan tới shift:** khi người dùng chọn một feature hoặc nhóm có shift, hiển thị các bản ghi mới/thay đổi đóng góp vào cửa sổ hiện tại, các giá trị của chúng so với baseline, report/batch/source và lineage transform. Cho phép lọc/tải danh sách theo quyền. Đây là các bản ghi liên quan về mặt thống kê, không tự chứng minh chúng gây ra shift.

### Luồng xem xét và huấn luyện lại

1. Dashboard cảnh báo shift hoặc suy giảm metric; người dùng xem baseline, cửa sổ hiện tại, cỡ mẫu, nhãn đã trưởng thành và các bản ghi liên quan.
2. Người có quyền chọn **đề xuất huấn luyện lại** với snapshot dữ liệu đã cập nhật. Trước khi chạy, hiển thị rõ khoảng ngày, nguồn/batch, quy tắc cleaning, định nghĩa target, số dòng/nhãn dùng được, tỷ lệ thiếu và phiên bản code/feature.
3. Huấn luyện thành một candidate version; đánh giá trên temporal holdout hoặc quy trình validation đã định trước. So sánh candidate với model đang chạy về performance, calibration, coverage theo các nhóm, độ bất định và các kiểm tra chất lượng. Tránh leakage bằng cách chỉ dùng thông tin sẵn có tại thời điểm dự đoán.
4. Chỉ người được phân quyền mới có thể phê duyệt promote candidate. Lưu người yêu cầu/duyệt, dataset snapshot, code/config, metrics và thời gian. Hỗ trợ từ chối, rollback về phiên bản trước và theo dõi sau triển khai. Không tự động ghi đè model đang hoạt động chỉ vì phát hiện shift.

Các kết quả huấn luyện lại cần được diễn giải theo đúng target và chất lượng nhãn. Với dữ liệu VAERS, số báo cáo và trường outcome tự báo cáo không phải tỷ lệ biến cố trong toàn bộ người tiêm; mô hình không được trình bày như công cụ chẩn đoán cá nhân nếu chưa có xác nhận và quy trình đánh giá phù hợp.

## Công việc dữ liệu/API cần có để truy vết đáng tin cậy

Warehouse hiện có các thành phần hữu ích: `meta.ingestion_batch` lưu nguồn, mode, trạng thái, thời gian và số dòng; `meta.ingestion_batch_row` lưu row hash đã thấy trong từng batch; `core.fct_report` có `batch_id`. Tuy nhiên, notebook hiện chỉ lưu artifact cục bộ, và các bridge fact symptom/vaccine không giữ lineage của từng raw row. Chỉ dựa vào `batch_id` cấp report thì chưa chứng minh được raw symptom/vaccine row nào làm đổi metric dẫn xuất.

Trước khi triển khai đầy đủ chức năng giải thích thay đổi, cần bổ sung:

1. **Lineage có phiên bản:** giữ batch thành công và raw row hash/version cho từng report, symptom, vaccine được dùng trong kết quả core đã publish. Phân biệt row thấy lần đầu với row được quan sát lại hoặc được sửa ở batch sau. Không coi row không đổi là dữ liệu mới chỉ vì nó xuất hiện trong snapshot sau.
2. **Snapshot phân tích đã publish:** lưu `run_id`/`snapshot_id`, `as_of`, transform/quality run ID, source batch IDs, phiên bản phân tích, bộ lọc, khoảng thời gian, metric/group key, value và denominator cho từng kết quả dashboard. Giữ snapshot so sánh trước đó để tái tạo delta.
3. **Bản ghi đóng góp vào delta:** lưu additions/revisions/removals cấp report và phần đóng góp vào metric giữa hai snapshot, nối được về lineage ở trên. Quyết định và ghi rõ thời hạn lưu cũng như quyền xem report ID.
4. **Analytics model và API:** cung cấp chuỗi xu hướng, delta so sánh, chi tiết đóng góp, dimension lọc và metadata qua endpoint có tham số an toàn, role API chỉ đọc. Mỗi response phải ghi `as_of`, phiên bản, nguồn và ngữ nghĩa mẫu số.
5. **Publish sau quality gate:** chỉ publish snapshot sau khi batch cần thiết, dbt transform và quality checks đã thành công. Giữ lịch sử lần chạy lỗi để vận hành, nhưng không trộn kết quả dở dang vào snapshot dashboard đang hoạt động.

Cho tới khi bổ sung các phần này, batch page có thể giải thích **khi nào và bao nhiêu dữ liệu đã được lấy**, và trend có thể nhóm theo ngày VAERS nhận. Nhưng dashboard chưa thể khẳng định đáng tin cậy raw row cụ thể nào làm thay đổi từng metric symptom/subgroup.

## Trang dashboard gợi ý

| Trang | Nội dung chính | Giải thích thay đổi |
|---|---|---|
| Tổng quan | Báo cáo theo ngày nhận, batch thành công gần nhất, quality status, symptom tăng/giảm nhiều | So sánh kỳ và danh sách report/batch đóng góp |
| Triệu chứng | Count và phần trăm báo cáo theo thời gian; lọc symptom/product/nhóm; phân bố onset-delay ở biểu đồ riêng | Báo cáo vào/ra tập symptom/nhóm và batch/transform làm đổi membership |
| Cohort | So sánh A12 theo product/dose-series/age/sex/year; hiện `n` và UNKNOWN rõ ràng | Báo cáo mới/sửa đổi và biến động mẫu số của từng nhóm |
| Quan hệ / hỗ trợ mô hình | Tín hiệu backend; predictions cạnh observed outcomes; metrics hiệu năng/calibration và distribution shift theo phiên bản/cửa sổ | Drill tới bản ghi/batch liên quan; so sánh candidate retrain với model hiện tại; lưu quyết định promote/rollback |
| Lineage dữ liệu | Lịch sử batch, raw snapshot, transform, quality và publication | Drill từ delta trên dashboard về source batch và report liên quan |

## Phạm vi tài liệu

Tài liệu này đặc tả hành vi và hợp đồng dữ liệu. Chưa triển khai trang dashboard, API route, analytics model, giám sát shift hay code dự báo/huấn luyện lại. Cần chốt target, nhãn thực tế, metric/threshold, lineage và quy trình validation/phê duyệt mô hình trước khi triển khai.
