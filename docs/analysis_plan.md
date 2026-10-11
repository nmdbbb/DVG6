# Kế hoạch phân tích — tái lập và mở rộng Flora et al. (2022)

Chủ: Analysis Lead & Quality Owner. Người thực hiện: Analysis & Visualization.

Tài liệu này dịch bài báo thành việc cụ thể trong repo: mỗi phân tích của bài báo tương ứng một notebook, một view `analytics`, và một biểu đồ trên dashboard. Bối cảnh và câu hỏi nghiên cứu: [business_case.md](business_case.md).

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

Nhóm **không chạy lại bằng R**. Mọi phân tích đọc từ `core`/`analytics` trong warehouse bằng Python, kết quả ghi ngược vào bảng để API phục vụ — không có con số nào chỉ tồn tại trong notebook ([data_contract.md §6](data_contract.md)).

| # | Phân tích | Hình/bảng gốc | Notebook | View phục vụ | Thư viện |
|---|---|---|---|---|---|
| A1 | Tần suất 20 triệu chứng hàng đầu theo nhà sản xuất | Table 1, Figure 1a | `01_eda_frequency.ipynb` | `v_ae_frequency_by_vaccine` | polars |
| A2 | Tần suất theo nhóm tuổi × giới tính (heatmap) | Table 2, Figure 1b | `02_age_sex_heatmap.ipynb` | `v_ae_by_age_sex` | polars |
| A3 | Kiểm định chi-square triệu chứng × giới, triệu chứng × nhóm tuổi | p-value trong §2 | `03_chi_square.ipynb` | `v_ae_significance` | scipy.stats |
| A4 | Phân cụm phân cấp triệu chứng × nhóm tuổi | Figure 2 | `04_clustering.ipynb` | `v_ae_cluster` | scipy.cluster.hierarchy |
| A5 | Association rule mining giữa các triệu chứng | Table 3, Table 4 | `05_arm.ipynb` | `v_ae_association_rules` | mlxtend (apriori + association_rules) |
| A6 | PCA / SOM trên ma trận báo cáo × triệu chứng | Figure 4 | `06_pca_som.ipynb` | `v_ae_component` | scikit-learn (PCA), minisom (tùy chọn) |
| A7 | Bipartite graph: dị ứng ↔ triệu chứng, nhà sản xuất ↔ triệu chứng | Figure 5 | `07_bipartite.ipynb` | `v_ae_allergen_link` | ECharts (vẽ ở frontend) |
| A8 | **So sánh dữ liệu thô và dữ liệu đã làm sạch** | §2, "7% variations" | `08_cleaning_impact.ipynb` | `v_cleaning_impact` | polars, scipy (Spearman) |

**SOM là tùy chọn.** Nếu thiếu thời gian thì dùng PCA — vừa nằm trong chương trình môn học, vừa dễ giải thích hơn. Ghi quyết định vào [decision_log.md](decision_log.md).

## 3. Quy tắc bắt buộc với phân tích

1. **Ngưỡng ghi trước.** Support, confidence, lift của ARM và mức ý nghĩa α phải ghi vào notebook **trước** khi chạy. Điểm khởi đầu đề xuất: `min_support = 0.01`, `min_confidence = 0.5`, giữ luật có `lift > 1`. Bài báo công bố các luật có support 0,011–0,028 và lift 3,3–18,8 nên ngưỡng này cho ra lượng luật tương đương.
2. **Đa kiểm định.** A3 chạy hàng trăm kiểm định (20 triệu chứng × 7 nhóm tuổi × 2 giới). Phải hiệu chỉnh Benjamini-Hochberg và báo cả p thô lẫn p hiệu chỉnh.
3. **Mọi notebook chạy lại được từ đầu.** Đọc bằng role `analyst`, không đọc file rời, không có ô nào phụ thuộc trạng thái ô trước đó đã bị xóa. Kernel restart + run all phải ra cùng kết quả.
4. **Kết quả ghi vào bảng.** Mỗi notebook ghi vào một bảng trong `analytics` kèm cột `run_id` và `as_of`, để dashboard và báo cáo lấy cùng một con số.
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

## 5. Quy tắc khử trùng lặp (đề xuất, Data Architect chốt)

Bài báo dùng phương pháp xác suất của một nghiên cứu khác và không công bố quy tắc cụ thể. Nhóm dùng quy tắc tất định, ghi rõ để người khác kiểm chứng được:

> Hai báo cáo là trùng nhau khi **trùng toàn bộ**: nhóm tuổi, giới tính, bang, ngày tiêm, nhà sản xuất vắc xin, và **tập triệu chứng đã chuẩn hóa**.

Giữ báo cáo có `VAERS_ID` nhỏ nhất (nộp sớm nhất), các bản còn lại đánh dấu là trùng và **không xóa khỏi `raw`** — chỉ loại ở tầng `core`. Số dòng trước/sau ghi vào [cleaning_log.md](cleaning_log.md).

Phải báo cáo **độ nhạy**: nếu đổi quy tắc (ví dụ bỏ điều kiện bang) thì tỉ lệ trùng lặp đổi bao nhiêu. Một con số 29% không có quy tắc kèm theo thì không kiểm chứng được.
