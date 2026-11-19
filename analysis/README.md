# Hướng dẫn chạy các notebook Analysis

## Mục đích và phạm vi

Notebook trong `analysis/notebooks/` thực hiện các phân tích A0–A12 trong
[`docs/analysis_plan.md`](../docs/analysis_plan.md). Notebook đọc warehouse bằng role
PostgreSQL `analyst` và hiện lưu CSV/hình cục bộ trong `analysis/reports/`; chúng chưa
publish kết quả vào PostgreSQL.

Mỗi notebook là entry point ngắn, còn truy vấn và phép tính được đặt trong
analysis/eda_workflows.py để tránh lệch logic giữa các lần chạy.

## Phân vai frontend/backend

- `notebooks/frontend/`: notebook tham chiếu cho biểu đồ và tương tác khám phá mà dashboard cần cung cấp.
- `notebooks/backend/`: notebook phân tích/profiling dùng để xác định feature và mối liên hệ ứng viên cho model. Không phải mọi notebook backend đều là kiểm định tương quan.
- Hai lớp hiện vẫn là notebook phân tích offline; dashboard production phải đọc các model `analytics` qua API, không import workflow Python hoặc đọc artifact notebook.

Danh sách vai trò và yêu cầu dashboard theo thời gian nằm trong
[`docs/dashboard_analysis_contract.md`](../docs/dashboard_analysis_contract.md).
`analysis/generate_notebooks.py` giữ việc sinh notebook đúng hai thư mục này.

Các workflow top-N giữ quy tắc chọn top-N đã ghi trong notebook; triệu chứng COVID-19
được giữ trong tập ứng viên và xuất hiện nếu đạt thứ hạng. A0 không chọn danh sách triệu chứng.

Phạm vi nghiên cứu theo decision #28 và #42 vẫn là năm 2021; `fct_report_raw` đang lọc cứng
2021. Các workflow notebook không tự lọc theo năm: chúng phân tích những dòng hiện diện trong
core và báo khoảng ngày ở notebook overview. Nếu core được mở rộng sang năm khác thì phải ghi
decision_log trước, và cột "năm" trong A3/A12 mới có nghĩa.

## Cách chuẩn bị và chạy

1. Khởi động Docker Desktop.
2. Trong terminal tại thư mục DVG6, chạy docker compose up -d db, rồi make migrate
   nếu role analyst chưa được tạo hoặc ANALYST_PASSWORD vừa đổi.
3. Cài dependency cho kernel Jupyter đang dùng:

       py -m pip install -r analysis/requirements.txt

4. Đặt ANALYST_PASSWORD trong DVG6/.env. Notebook kết nối local tại localhost:5432,
   database qtdl, user analyst. Không lưu URL owner trong notebook.
5. Chạy `frontend/00_eda_overview.ipynb`, rồi notebook cần thiết trong `frontend/` hoặc
   `backend/`. Dùng Restart Kernel and Run All để chạy lại từ đầu.

Nếu thiếu relation hoặc bảng rỗng, workflow báo rõ điều kiện chưa đạt. make transform
chỉ tạo những model có file SQL; không thể tự tạo bridge fact chưa được triển khai.

## Danh sách notebook

| Notebook | Mục tiêu | Bảng core chính | Đầu ra |
|---|---|---|---|
| 00_eda_overview.ipynb | Quy mô, độ đầy đủ, nhân khẩu học, xu hướng thời gian | fct_report và dimensions | CSV profile/counts, biểu đồ theo tháng |
| 01_eda_frequency.ipynb | A1: top 10 triệu chứng theo hãng | symptom/vaccine facts và dimensions | Bảng tần suất, phần trăm, hình |
| 02_age_sex_heatmap.ipynb | A2: top 10 triệu chứng theo nhóm tuổi × giới | report/symptom facts, age/sex/symptom dimensions | Hai bảng tỷ lệ (male, female), heatmap tách theo giới |
| 03_correlation_all_symptoms.ipynb | A3: kiểm định độc lập giữa các biến phân loại | report, symptom, vaccine, age và sex facts/dimensions | Bốn bảng chéo, Chi-square, p đã hiệu chỉnh và Cramer's V |
| 04_clustering.ipynb | A4: phân cụm hồ sơ triệu chứng theo tuổi | report/symptom facts, age/symptom dimensions | Ma trận hồ sơ tuổi, dendrogram |
| 05_arm.ipynb | A5: luật triệu chứng đồng xuất hiện | report/symptom facts, symptom dimension | Luật với support, confidence, lift |
| 06_som.ipynb | A6: SOM trên ma trận báo cáo × triệu chứng | report/symptom facts | component planes, U-Matrix, neuron assignments và codebook |
| 07_bipartite.ipynb | A7: liên kết dị ứng/hãng với top 10 triệu chứng | allergen/vaccine/symptom facts, dimensions | CSV cạnh, hình top cạnh dị ứng |
| 08_cleaning_impact.ipynb | A8: box plot phân bố tuổi theo top 10 triệu chứng | report/symptom facts, symptom dimension | Bảng count, min, Q1, median, Q3, max và whisker; box plot tuổi theo triệu chứng |
| 09_onset_timing.ipynb | A9: onset lag từ VAX_DATE đến ONSET_DATE | report/symptom facts, symptom dimension | Box plot top 5; histogram khi chọn symptom cụ thể; CSV thống kê |
| 10_outcomes_by_symptom.ipynb | A10: cờ kết quả theo triệu chứng | report, symptom, vaccine, age facts/dimensions | Heatmap phần trăm kèm số báo cáo có cờ / mẫu số |
| 11_symptom_cooccurrence.ipynb | A11: symptom co-occurrence | report/symptom facts, symptom dimension | Count and lift heatmaps; pair metrics CSV |
| 12_symptom_by_group.ipynb | A12: compare symptom percentages by vaccine, dose series, age, sex, or year | report/vaccine/symptom facts and dimensions | Filterable small-multiple heatmap with subgroup n; detailed CSV |

## Phương pháp và giả định theo notebook

### A1 — Tần suất theo hãng

Top 10 symptoms, including COVID-19 and SARS-CoV-2 test-positive entries when they rank in the top 10, are selected by distinct report count. The distinct
report_key–manufacturer được tạo trước khi nối symptom fact để một báo cáo không bị
đếm lặp cho cùng hãng. Biểu đồ cột nhóm dùng phần trăm báo cáo của từng hãng trên
trục Y; mẫu số là tổng báo cáo có hãng đó. Một báo cáo có thể thuộc nhiều hãng nếu
nguồn có nhiều sản phẩm.

### A2 — Heatmap tuổi và giới

Giới hạn heatmap ở top 10 triệu chứng theo số báo cáo, bỏ hai triệu chứng trên; loại nhóm tuổi/giới UNKNOWN khỏi so sánh. Tỷ lệ là số báo cáo trong nhóm có triệu
chứng chia cho tổng số báo cáo của nhóm. Một báo cáo có nhiều triệu chứng nên tổng
các phần trăm triệu chứng không bằng 100%.

### A3 — Kiểm định độc lập giữa các biến phân loại

Top 10 most reported symptoms are selected, including COVID-19 and SARS-CoV-2 test-positive entries when they rank in the top 10. For each report, the selected symptom set is
thành một biến phân loại `symptom_profile`; mỗi báo cáo đóng góp đúng một lần vào từng
bảng chéo. Nhà sản xuất là một biến phân loại: nếu báo cáo có nhiều hãng thì gán nhóm
`MULTIPLE`; thiếu hãng gán `UNKNOWN`. Kiểm định Chi-square độc lập tổng thể được chạy
cho bốn cặp `manufacturer × symptom_profile`, `report_year × symptom_profile`,
`age_group × symptom_profile` và `gender × symptom_profile`. UNKNOWN age/gender được
loại khỏi hai kiểm định tương ứng, giống quy tắc A2.
Hồ sơ triệu chứng xuất hiện dưới 5 báo cáo được gộp thành `OTHER / RARE PROFILES`.
Kết quả gồm Chi-square, bậc tự do, p, p hiệu chỉnh Bonferroni cho bốn kiểm định,
Cramer's V và số ô có tần suất kỳ vọng dưới 5. Đây là kiểm định liên hệ tổng thể giữa
hai biến, không phải kiểm định riêng từng hãng hay từng triệu chứng; liên hệ không
chứng minh quan hệ nhân quả.

### A4 — Phân cụm

Lấy tối đa 10 triệu chứng phổ biến sau khi loại hai triệu chứng trên, tính phân bố báo cáo qua 7 nhóm tuổi đã biết,
chuẩn hóa từng triệu chứng thành tỷ trọng rồi dùng cosine distance và average linkage.
Cụm mô tả độ giống hồ sơ báo cáo, không đại diện nhóm bệnh nhân hay cơ chế y học.

### A5 — Association rules

Ngưỡng khai báo trước: min_support = 0.01, min_confidence = 0.50, lift > 1,
max_len = 3. Candidate set giới hạn 10 triệu chứng phổ biến, bỏ hai triệu chứng trên, để kiểm soát bộ nhớ.
Support dùng tổng số báo cáo clean làm mẫu số.

### A6 — SOM

Huấn luyện Self-Organizing Map lục giác trên ma trận nhị phân report × tối đa 10
symptoms, including COVID-19-related entries when they rank in the top 10; choose at most 10,000 reports in deterministic MD5 order so the sample is reproducible.
tạo. Seed, kích thước lưới 15 × 15 và số vòng lặp được cố định trong workflow.
`06_som_component_planes.png` tô trọng số prototype của từng triệu chứng trên cùng
một bản đồ (thang 0–1); vùng ấm ở hai mặt phẳng gần nhau gợi ý kiểu báo cáo tương tự,
không chứng minh tương quan hay nhân quả. `06_som_umatrix.png` tô khoảng cách giữa
prototype lân cận để thấy ranh giới vùng; `06_som_neuron_occupancy.csv` cho biết số
báo cáo được ánh xạ vào từng neuron. Mỗi neuron là một kiểu hồ sơ mẫu, không phải một
báo cáo. A6 hiện thuần SOM, không chạy PCA.

### A7 — Đồ thị liên kết

Dùng top 10 triệu chứng sau khi loại hai triệu chứng trên và COUNT DISTINCT report_key để tránh fan-out. Cạnh allergen chỉ lấy match exact
hoặc fuzzy, loại UNMAPPED; chỉ giữ cạnh có ít nhất 50 báo cáo. Cạnh manufacturer–
symptom dùng cùng ngưỡng. Cạnh thể hiện đồng xuất hiện trong báo cáo VAERS.

### A8 — Box plot độ tuổi theo triệu chứng

The top 10 symptoms by distinct report count include COVID-19 and SARS-CoV-2 test-positive entries when ranked in the top 10. Each observation is a report-symptom pair; missing ages or ages outside 0-120 are excluded. Boxes show Q1-Q3 and median; whiskers use 1.5 x IQR. Outliers are hidden in the plot; min/max remain in the CSV. A report can appear under multiple symptoms.

Đầu ra: `08_age_by_symptom_boxplot.png` và `08_age_by_symptom_boxplot_stats.csv`.

## Điều kiện tiên quyết hiện tại

Data contract và hd_goi_data_transform.md mô tả ba bridge fact:
core.fct_report_symptom, core.fct_report_vaccine và core.fct_report_allergen.
Nhưng transform/models/core hiện chưa có model SQL cho các bảng này. Notebook cần
bridge table sẽ dừng và chỉ rõ relation bị thiếu. Chạy lại dbt không tạo được bảng
khi chưa có model; Transform cần bổ sung model, grain, description và kiểm tra khóa.

Trong phiên làm việc này, truy vấn local cho fct_report_raw và fct_report trả 0 dòng.
Ngoài ra, model fct_report_raw.sql trong working copy vẫn có điều kiện kết thúc năm
2021 (điều kiện ngày bắt đầu đang comment), dù decision log đã mở rộng phạm vi.
Transform cần đồng bộ phạm vi trước khi các notebook có thể mô tả 2021–2026.
Dimension ngày cũng cần bao phủ ngày năm 2026. Cần ingestion VAERS thành công, chạy
transform và quality trước khi diễn giải kết quả. Quality pass của source_demo không
chứng minh chất lượng VAERS.

## Kết quả dùng cho API

Notebook lưu artifact cục bộ, không ghi bảng analytics vì role analyst chỉ có SELECT.
analysis_plan.md yêu cầu kết quả phục vụ API/dashboard được lưu trong warehouse với
run_id và as_of. Khi cần đưa kết quả lên dashboard, Transform/Data Architect cần tạo
model analytics và quy trình ghi kết quả có kiểm soát.

VAERS không có mẫu số liều tiêm và không chứng minh vaccine gây ra sự kiện. Diễn giải
kết quả là tần suất trong tập báo cáo.

### A9 — Thời gian từ tiêm đến khởi phát

Tính số ngày `ONSET_DATE - VAX_DATE` ở cấp báo cáo, chỉ giữ ngày hợp lệ và onset không trước ngày tiêm. Mặc định tạo box plot cho top 5 triệu chứng. Trong ô cấu hình của notebook, đặt `selected_symptom` bằng tên chuẩn để tạo thêm histogram riêng cho triệu chứng đó. Vì VAERS chỉ có ngày khởi phát ở cấp báo cáo, thời gian này không phải ngày khởi phát riêng của từng symptom trong báo cáo nhiều triệu chứng.

Đầu ra: `09_onset_delay_top5_boxplot.png`, `09_onset_delay_top5_stats.csv`; khi chọn symptom, thêm `09_onset_delay_selected_symptom_histogram.png` và `09_onset_delay_selected_symptom_stats.csv`.

### A10 — Cờ kết quả nghiêm trọng theo triệu chứng

Tính distinct report có cờ nhập viện, cấp cứu, đe dọa tính mạng, khuyết tật hoặc tử vong trên tổng distinct report có symptom. Mặc định lấy top 10 symptom trong cohort sau lọc; có thể xem riêng một symptom, kể cả khi không nằm trong top 10, hoặc lọc theo từ khóa vaccine, nhóm tuổi và khoảng `numdays`. Mỗi cờ được tính riêng nên các cột không cộng thành 100%.

Các cờ là thông tin trên report VAERS, có thể chưa được xác minh. Trong core, giá trị không phải Y (kể cả giá trị thiếu) thành false; do đó phần trăm là số report có cờ Y trên tổng report có symptom, không phải tỷ lệ outcome trong những report có thông tin outcome đầy đủ.

Đầu ra: `10_outcomes_by_symptom_heatmap.png` và `10_outcomes_by_symptom.csv`.


### A11 - Symptom co-occurrence

A11 builds a report-by-symptom binary matrix from the top 10 symptom terms and counts distinct reports containing each pair. The count heatmap shows co-reports; the lift heatmap compares observed support with the support expected under independence. The pair table includes support (co-reports divided by all distinct reports), P(B|A), P(A|B), and lift. The diagonal is omitted from lift because a symptom paired with itself is not informative. These are report co-mentions, not causal or patient-level relationships.

Run `frontend/11_symptom_cooccurrence.ipynb`; outputs are `11_symptom_cooccurrence_heatmaps.png` and `11_symptom_cooccurrence_pairs.csv`. Set `top_n` and `min_pair_reports` in the notebook to adjust the display group and minimum pair count in the CSV.


### A12 - Compare symptom reporting across groups

A12 lets the analyst choose two different dimensions from product, manufacturer, dose series, age group, sex, and report year. For every observed group pair and each selected symptom, the CSV reports the distinct subgroup report count, distinct reports with the symptom, and percentage. Missing/unspecified values are retained as UNKNOWN. The heatmap shows the top five symptoms by default; set an exact `selected_symptom` to show one symptom, and set `top_n` to change the CSV symptom set.

The chart limits each axis to the 10 largest groups plus UNKNOWN when present; the CSV keeps all observed groups. VAERS can record multiple vaccines on one report, so a report may appear in multiple product/manufacturer/dose-series groups. These are report percentages, not rates among vaccinated people. The source provides `dose_series`, not a separate per-product dose number.

Outputs: `12_symptom_percentage_by_group.png` and `12_symptom_percentage_by_group.csv`.
