# Business case

**Topic chốt 2026-10-11:** phản ứng bất lợi sau tiêm vắc xin COVID-19, dựa trên dữ liệu VAERS.

Bài báo nền: Flora J., Khan W., Jin J., Jin D., Hussain A., Dajani K., Khan B. (2022). *Usefulness of Vaccine Adverse Event Reporting System for Machine-Learning Based Vaccine Research: A Case Study for COVID-19 Vaccines.* **Int. J. Mol. Sci. 23(15), 8235.** [doi:10.3390/ijms23158235](https://doi.org/10.3390/ijms23158235) (open access, CC BY).

## Bài toán nghiệp vụ

VAERS là hệ thống báo cáo **thụ động**: ai cũng nộp được, không ai kiểm tra trước. Hệ quả là dữ liệu có trùng lặp, thiếu, sai chính tả, và không có mẫu số (số liều đã tiêm). Người dùng — cơ quan quản lý, nhà sản xuất, bác sĩ tư vấn — cần biết **triệu chứng nào được báo nhiều, ở nhóm người nào, đi kèm triệu chứng nào**, để ưu tiên theo dõi an toàn vắc xin.

Rủi ro nếu dữ liệu không được làm sạch: Flora et al. đo được kết quả phân tích **lệch khoảng 7%** giữa dữ liệu thô và dữ liệu đã làm sạch, và 29% báo cáo là trùng lặp. Kết luận rút ra từ dữ liệu thô có thể xếp sai thứ hạng triệu chứng, tức là hướng sự chú ý của cơ quan quản lý vào sai chỗ.

Đây chính là lý do topic này hợp môn Quản trị dữ liệu: **giá trị của phân tích phụ thuộc trực tiếp vào chất lượng dữ liệu, và mức phụ thuộc đó đo được bằng số.**

## Câu hỏi nghiên cứu

| # | Câu hỏi | View phục vụ | Trang dashboard |
|---|---|---|---|
| Q1 | Triệu chứng nào được báo nhiều nhất sau mỗi vắc xin (Pfizer-BioNTech, Moderna, Janssen), và khác nhau thế nào giữa ba nhà sản xuất? | `v_ae_frequency_by_vaccine` | Explore |
| Q2 | Hồ sơ triệu chứng thay đổi thế nào theo **nhóm tuổi** và **giới tính**? | `v_ae_by_age_sex` | Explore, Analysis |
| Q3 | Tiền sử **dị ứng** có liên quan tới triệu chứng nào? | `v_ae_by_allergen` | Analysis |
| Q4 | Triệu chứng nào **đi kèm nhau** (luật kết hợp, cụm)? | `v_ae_association_rules`, `v_ae_cooccurrence` | Analysis |
| Q5 | **Làm sạch dữ liệu thay đổi kết luận bao nhiêu?** So Q1–Q4 trên dữ liệu thô và dữ liệu đã làm sạch. | `v_cleaning_impact` | Analysis, Pipeline health |

Q5 là đóng góp riêng của nhóm và là trọng tâm môn học: bài báo nêu con số 7% nhưng không công bố quy trình đo. Nhóm đo lại bằng pipeline của mình, mỗi bước làm sạch một dòng trong [cleaning_log.md](cleaning_log.md).

## Kế hoạch thống kê

| Câu hỏi | Biến phụ thuộc | Biến giải thích | Phương pháp | Giả định cần kiểm |
|---|---|---|---|---|
| Q1 | Tần suất tương đối của mỗi triệu chứng | Nhà sản xuất vắc xin | Bảng tần suất + kiểm định chi-square tính độc lập | Ô kỳ vọng ≥ 5; báo cáo độc lập nhau (không giữ được hoàn toàn — ghi rõ là hạn chế) |
| Q2 | Có/không báo một triệu chứng | Nhóm tuổi (7 nhóm), giới tính | Chi-square theo từng cặp + hiệu chỉnh đa kiểm định (Benjamini-Hochberg) | Như trên; nhóm tuổi phải đủ cỡ mẫu |
| Q3 | Có/không báo một triệu chứng | Dị ứng đã chuẩn hóa | Chi-square + odds ratio kèm khoảng tin cậy | Dị ứng là văn bản tự do → sai số phân loại; đo mức chuẩn hóa được |
| Q4 | Đồng xuất hiện triệu chứng | — | Association rule mining (support/confidence/lift), phân cụm phân cấp trên ma trận tần suất, PCA | Ngưỡng support/confidence phải ghi trước, không chọn sau khi thấy kết quả |
| Q5 | Độ lệch của Q1–Q4 | Có/không làm sạch | Chạy cùng một quy trình trên hai tập, so thứ hạng (Spearman) và tần suất (độ lệch tuyệt đối) | Hai tập chỉ khác nhau ở bước làm sạch, mọi thứ khác giữ nguyên |

**Những điều KHÔNG được kết luận** (ghi rõ trong báo cáo):

- VAERS **không chứng minh nhân quả.** Một báo cáo chỉ nói "sự việc xảy ra sau khi tiêm", không nói "do tiêm".
- **Không có mẫu số.** Không biết tổng số liều đã tiêm theo nhóm tuổi, nên không tính được tỉ lệ biến cố trên 100.000 liều. Mọi con số là **tần suất tương đối trong nội bộ báo cáo VAERS**, không phải nguy cơ.
- **Thiên lệch báo cáo.** Vắc xin mới và truyền thông mạnh làm tăng số báo cáo mà không làm tăng biến cố thật.

## Phạm vi và giới hạn

| Mục | Quyết định |
|---|---|
| Thời gian | Báo cáo nhận trong 2021 (năm đầu triển khai COVID-19), file `2021VAERSData.zip`. Mở rộng 2020–2022 nếu đủ thời gian. |
| Vắc xin | `VAX_TYPE = 'COVID19'`, ba nhà sản xuất: Pfizer-BioNTech, Moderna, Janssen. |
| Địa lý | Báo cáo trong nước Mỹ. Bộ Non-Domestic bị cơ quan quản lý châu Âu yêu cầu xóa nhiều trường nên không dùng. |
| Nhóm tuổi | 7 nhóm theo bài báo: 5–11, 12–15, 16–18, 19–30, 31–50, 51–65, 66+. |

Quyết định phạm vi và mọi đánh đổi: [decision_log.md](decision_log.md). Cách làm từng phân tích: [analysis_plan.md](analysis_plan.md).
