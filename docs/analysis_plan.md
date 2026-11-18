# Kế hoạch phân tích — tái lập và mở rộng Flora et al. (2022)

Chủ: Analysis Lead & Quality Owner. Người thực hiện: Analysis & Visualization.

Tài liệu này ánh xạ các câu hỏi phân tích vào notebook và đầu ra dự kiến. Chia sẻ vai trò notebook, hợp đồng visualization/model và đặc tả dashboard theo thời gian được mô tả trong [dashboard_analysis_contract.md](dashboard_analysis_contract.md). Bối cảnh và câu hỏi nghiên cứu: [business_case.md](business_case.md).

**Trạng thái triển khai:** notebook hiện đọc `core`, lưu artifact CSV/PNG cục bộ và chưa ghi vào `analytics`. Các view/API dashboard trong bảng dưới là đầu ra mục tiêu, không có nghĩa tất cả đã tồn tại. Dashboard production không chạy notebook; Transform/API cần cung cấp model và endpoint có phiên bản, mẫu số, `as_of` và lineage.

## 1. Bài báo làm gì

| Phần bài báo | Nội dung | Con số mốc để đối chiếu |
|---|---|---|
| Dữ liệu | VAERS, 3 vắc xin COVID-19 | 905.976 báo cáo thô |
| Làm sạch | Bỏ báo cáo không có triệu chứng | còn 892.213 |
| Làm sạch | Gộp trùng lặp + sửa chính tả | còn **643.522** (trùng lặp 29%) |
| Làm sạch | Bỏ báo cáo thiếu tuổi (chỉ cho phân tích tuổi/giới) | 63.189 báo cáo |
| Làm sạch | Rời rạc hóa tuổi thành 7 nhóm | 5–11, 12–15, 16–18, 19–30, 31–50, 51–65, 66+ |
| Kết quả | 20 triệu chứng được báo nhiều nhất | 6 triệu chứng đầu chiếm >50% |
| Kết quả | Moderna nhiều phản ứng tại chỗ tiêm hơn | +15,2%, p < 2,2 × 10⁻¹⁶ |
| Kết quả | Đau ngực ở bé trai so với bé gái | +295%, chi-square p = 5,74 × 10⁻⁶² |
| Kết quả | Dị ứng hay gặp nhất | penicillin 22%, sulfa 19%; ~14% viết sai chính tả |
| Kết quả | Ảnh hưởng của việc làm sạch | kết quả lệch ~7% |

Công cụ bài báo dùng: R `arules` 1.7-3 (ARM), `kohonen` 3.0.11 (SOM), `hclust` (phân cụm), Python `stats.chisquare`, `d3.js` (bipartite graph).

## 2. Nhóm làm gì

Nhóm **không chạy lại bằng R**. Notebook Python đọc warehouse bằng role `analyst`; artifact notebook là để tái tạo phân tích và rà soát. Khi kết quả được dùng trong dashboard, chúng phải được materialize thành model `analytics` có kiểm soát và phục vụ qua API read-only, không để API phụ thuộc vào file notebook hoặc CSV/PNG cục bộ.

| # | Phân tích | Hình/bảng gốc | Notebook | Đầu ra hiện tại / đích analytics | Thư viện |
|---|---|---|---|---|---|
| A1 | Tần suất 10 triệu chứng hàng đầu theo nhà sản xuất | Table 1, Figure 1a | `frontend/01_eda_frequency.ipynb` | `v_ae_frequency_by_vaccine` | polars |
| A2 | Tần suất theo nhóm tuổi × giới tính (heatmap) | Table 2, Figure 1b | `backend/02_age_sex_heatmap.ipynb` | `v_ae_by_age_sex` | polars |
| A3 | Kiểm định độc lập symptom profile với nhà sản xuất/năm/nhóm tuổi/giới | Chi-square, p hiệu chỉnh Bonferroni, Cramer's V | `backend/03_correlation_all_symptoms.ipynb` | Bốn bảng chéo và kết quả kiểm định trong `analysis/reports/tables/` | scipy.stats.chi2_contingency |
| A4 | Phân cụm phân cấp triệu chứng × nhóm tuổi | Figure 2 | `backend/04_clustering.ipynb` | `v_ae_cluster` | scipy.cluster.hierarchy |
| A5 | Association rule mining giữa các triệu chứng | Table 3, Table 4 | `backend/05_arm.ipynb` | `v_ae_association_rules` | mlxtend (apriori + association_rules) |
| A6 | SOM trên ma trận báo cáo × triệu chứng | Figure 4 | `backend/06_som.ipynb` | `v_ae_component` | MiniSom |
| A7 | Bipartite graph: dị ứng ↔ triệu chứng, nhà sản xuất ↔ triệu chứng | Figure 5 | `backend/07_bipartite.ipynb` | `v_ae_allergen_link` | ECharts (vẽ ở frontend) |
| A8 | **Phân bố độ tuổi theo triệu chứng** | So sánh phân bố tuổi giữa các triệu chứng | `backend/08_cleaning_impact.ipynb` | `core.fct_report` + `core.fct_report_symptom` | PostgreSQL percentile, matplotlib box plot |
| A9 | **Thời gian từ tiêm đến khởi phát** | Phân bố ngày từ `VAX_DATE` đến `ONSET_DATE`; top 5 mặc định, histogram theo symptom được chọn | `frontend/09_onset_timing.ipynb` | `core.fct_report`, `core.fct_report_symptom`, `core.dim_symptom` | PostgreSQL percentile, matplotlib |
| A10 | **Cờ outcome nghiêm trọng theo symptom** | Số report và % report có cờ theo top symptom hoặc symptom chọn; lọc product/age/onset | `frontend/10_outcomes_by_symptom.ipynb` | `core.fct_report`, `core.fct_report_symptom`, `core.fct_report_vaccine`, dimensions | PostgreSQL aggregate, matplotlib heatmap |
| A11 | Symptom co-occurrence across reports | Pair counts, support, P(B|A), P(A|B), lift; co-occurrence and lift heatmaps | `frontend/11_symptom_cooccurrence.ipynb` | `11_symptom_cooccurrence_pairs.csv`, `11_symptom_cooccurrence_heatmaps.png` | PostgreSQL aggregation, pandas, matplotlib |
| A12 | Symptom reporting by product/manufacturer/dose series/age/sex/year | Group report count, symptom report count, percent; subgroup `n` shown and unknown retained | `frontend/12_symptom_by_group.ipynb` | `12_symptom_percentage_by_group.csv`, `12_symptom_percentage_by_group.png` | PostgreSQL aggregation, pandas, matplotlib |

**A6 dùng SOM thuần.** Component planes và U-Matrix là biểu diễn khám phá cấu trúc báo cáo; chúng không thay thế kiểm định thống kê hoặc các chỉ số ARM.

A1-A12 keep COVID-19-related symptom entries eligible for analysis; a top-N workflow includes them when they rank within its selected N.

## 3. Quy tắc bắt buộc với phân tích

1. **Ngưỡng ghi trước.** Support, confidence và lift của ARM phải ghi vào notebook **trước** khi chạy. Điểm khởi đầu đề xuất: `min_support = 0.01`, `min_confidence = 0.5`, giữ luật có `lift > 1`. Bài báo công bố các luật có support 0,011–0,028 và lift 3,3–18,8 nên ngưỡng này cho ra lượng luật tương đương.
2. **Diễn giải kiểm định.** A3 kiểm định độc lập tổng thể giữa hồ sơ triệu chứng tạo từ top 10 triệu chứng với nhà sản xuất, năm, nhóm tuổi và giới. UNKNOWN age/gender bị loại ở hai kiểm định tương ứng. Hồ sơ xuất hiện dưới 5 báo cáo được gộp để giảm bảng thưa; xem số ô có tần suất kỳ vọng dưới 5 trước khi diễn giải Chi-square. Kết quả không đo nguy cơ và không chứng minh quan hệ nhân quả.
3. **Mọi notebook chạy lại được từ đầu.** Đọc bằng role `analyst`, không đọc file rời, không có ô nào phụ thuộc trạng thái ô trước đó đã bị xóa. Kernel restart + run all phải ra cùng kết quả.
4. **Kết quả dashboard có snapshot.** Trước khi một phân tích được đưa lên dashboard, model phục vụ cần lưu `run_id`/`snapshot_id`, `as_of`, phiên bản phân tích, cửa sổ thời gian, bộ lọc, metric/group key, value, denominator, batch nguồn và transform/quality run để tái tạo cùng một con số và giải thích delta.
5. **Không kết luận nhân quả.** Dùng "được báo cáo nhiều hơn", không dùng "gây ra". Người duyệt (Analysis Lead) chặn PR vi phạm.

## 4. Đối chiếu với bài báo

Số của nhóm **sẽ không trùng** số của bài báo, vì khác khoảng thời gian, khác phiên bản dữ liệu (từ 5/2025 VAERS công bố thêm secondary report), và khác quy tắc khử trùng lặp. Yêu cầu là **giải thích được vì sao lệch**, không phải trùng khít.

Bảng đối chiếu bắt buộc có trong báo cáo cuối:

| Chỉ số | Bài báo | Nhóm | Chênh lệch | Giải thích |
|---|---|---|---|---|
| Số báo cáo thô | 905.976 | | | |
| Tỉ lệ trùng lặp | 29% | | | |
| 6 triệu chứng đầu chiếm | >50% | | | |
| Penicillin trong tổng dị ứng | 22% | | | |
| Lệch do làm sạch | ~7% | | | |

## 5. Quy tắc khử trùng lặp (`rule_version = 1`)

Bài báo dùng phương pháp xác suất của một nghiên cứu khác và không công bố quy tắc cụ thể. Nhóm dùng quy tắc tất định, ghi rõ để người khác kiểm chứng được:

> Hai báo cáo là trùng nhau khi **trùng toàn bộ** sáu thuộc tính: nhóm tuổi, giới tính, bang, ngày tiêm, tập nhà sản xuất vắc xin, và **tập triệu chứng đã chuẩn hóa**.

Định nghĩa chính xác (Transform cài đặt đúng từng chữ):

1. **Phạm vi so sánh:** chỉ các báo cáo đã qua bộ lọc của [data_contract.md §1](data_contract.md) (COVID19, trong nước) và có ít nhất một triệu chứng.
2. **Tập triệu chứng** = các `symptom_key` khác nhau của báo cáo, sau chuẩn hóa chính tả (`vaccination site` → `injection site`), so sánh nguyên tập; khác một phần tử là không trùng. **Tập nhà sản xuất** = các nhà sản xuất khác nhau trong dòng vắc xin COVID19 của báo cáo, so sánh nguyên tập.
3. **Điều kiện đủ để xét trùng:** `age_group`, `sex` và `vax_date` đều đã biết. Báo cáo thiếu một trong ba **không bao giờ bị đánh dấu trùng** (thiếu thông tin thì không đủ bằng chứng để gộp, và coi UNKNOWN = UNKNOWN sẽ gộp nhầm hàng loạt). `state` không bắt buộc: hai báo cáo cùng `state = UNKNOWN` được coi là cùng giá trị.
4. **Giữ lại:** trong mỗi nhóm trùng, giữ báo cáo có `VAERS_ID` nhỏ nhất, so sánh **như số nguyên** (không so chuỗi).
5. **Không xóa khỏi `raw`.** Báo cáo bị loại ghi vào `core.report_duplicate_map(vaers_id, kept_vaers_id, rule_version)`, vắng mặt ở `fct_report` nhưng vẫn có ở `fct_report_raw`.
6. Số dòng trước/sau ghi vào [cleaning_log.md](cleaning_log.md).

Báo cáo **độ nhạy** bắt buộc, chạy lại với: (a) bỏ điều kiện bang; (b) thay nhóm tuổi bằng `AGE_YRS` chính xác; (c) bỏ điều kiện ngày tiêm. Ghi tỉ lệ trùng lặp của từng biến thể cạnh `rule_version = 1`. Một con số 29% không có quy tắc kèm theo thì không kiểm chứng được.
