"""Generate the thin, reproducible Jupyter entry points for analysis workflows."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "analysis" / "notebooks"

# Keep generated entry points aligned with the hand-maintained frontend/backend split.
FRONTEND_NOTEBOOKS = {
    "00_eda_overview.ipynb",
    "01_eda_frequency.ipynb",
    "09_onset_timing.ipynb",
    "10_outcomes_by_symptom.ipynb",
    "11_symptom_cooccurrence.ipynb",
    "12_symptom_by_group.ipynb",
}
BACKEND_NOTEBOOKS = {
    "02_age_sex_heatmap.ipynb",
    "03_correlation_all_symptoms.ipynb",
    "04_clustering.ipynb",
    "05_arm.ipynb",
    "06_som.ipynb",
    "07_bipartite.ipynb",
    "08_cleaning_impact.ipynb",
}
for layer in ("frontend", "backend"):
    (NOTEBOOK_DIR / layer).mkdir(parents=True, exist_ok=True)

SETUP = """import sys
from pathlib import Path

project_dir = Path.cwd().resolve()
while not (project_dir / "Makefile").is_file() and project_dir != project_dir.parent:
    project_dir = project_dir.parent
if not (project_dir / "Makefile").is_file():
    raise FileNotFoundError("Không tìm thấy thư mục gốc DVG6")
sys.path.insert(0, str(project_dir))

from IPython.display import display
from analysis.notebook_utils import FIGURES_DIR, TABLES_DIR
"""

WORKFLOWS = [
    (
        "00_eda_overview.ipynb",
        "EDA tổng quan VAERS",
        "Kiểm tra các relation core, quy mô bảng, độ đầy đủ của thuộc tính báo cáo, phân bố nhân khẩu học và xu hướng theo thời gian trong phạm vi đang có ở core.",
        "run_overview",
    ),
    (
        "01_eda_frequency.ipynb",
        "A1 — Tần suất triệu chứng theo hãng vắc xin",
        "Select the 10 most reported symptoms, including COVID-19-related entries if they rank in the top 10, and compare rates by manufacturer.",
        "run_a1",
    ),
    (
        "02_age_sex_heatmap.ipynb",
        "A2 — Heatmap triệu chứng theo nhóm tuổi và giới",
        "Describe report percentages for the top 10 symptoms, including COVID-19-related entries when ranked in the top 10, by age and sex; exclude UNKNOWN demographic groups.",
        "run_a2",
    ),
    (
        "03_correlation_all_symptoms.ipynb",
        "A3 — Kiểm định độc lập giữa các biến phân loại",
        "Use chi-square and Cramer's V to test overall independence against profiles formed from the top 10 symptoms, including COVID-19-related entries when ranked in the top 10.",
        "run_a3",
    ),
    (
        "04_clustering.ipynb",
        "A4 — Phân cụm triệu chứng theo nhóm tuổi",
        "Cluster age profiles for the 10 most reported symptoms, including COVID-19-related entries when ranked in the top 10.",
        "run_a4",
    ),
    (
        "05_arm.ipynb",
        "A5 — Association rule mining",
        "Mine rules from up to 10 common symptoms, including COVID-19-related entries when ranked in the top 10; support=0.01, confidence=0.50, lift>1.",
        "run_a5",
    ),
    (
        "06_som.ipynb",
        "A6 — SOM trên ma trận báo cáo × triệu chứng",
        "Train SOM on up to 10 common symptoms, including COVID-19-related entries when ranked in the top 10, using at most 10,000 reports.",
        "run_a6",
    ),
    (
        "07_bipartite.ipynb",
        "A7 — Liên kết dị ứng và hãng với triệu chứng",
        "Build allergen/manufacturer edges for the top 10 symptoms, including COVID-19-related entries when ranked in the top 10.",
        "run_a7",
    ),
    (
        "08_cleaning_impact.ipynb",
        "A8 — Phân bố độ tuổi theo triệu chứng",
        "Compare age distributions by top 10 symptoms, including COVID-19-related entries when ranked in the top 10; exclude missing ages and ages outside 0?120.",
        "run_a8",
    ),
    (
        "09_onset_timing.ipynb",
        "A9 — Thời gian từ tiêm đến khởi phát",
        "So sánh thời gian từ ngày tiêm đến ngày khởi phát ở cấp báo cáo. Mặc định hiển thị box plot top 5 triệu chứng; có thể chọn một triệu chứng để thêm histogram.",
        "run_a9",
    ),
    (
        "10_outcomes_by_symptom.ipynb",
        "A10 — Cờ kết quả nghiêm trọng theo triệu chứng",
        "Hiển thị số báo cáo và phần trăm báo cáo có cờ nhập viện, cấp cứu, đe dọa tính mạng, khuyết tật hoặc tử vong theo top triệu chứng.",
        "run_a10",
    ),
    (
        "11_symptom_cooccurrence.ipynb",
        "A11 — Đồng xuất hiện của các triệu chứng",
        "Đo mức độ hai triệu chứng cùng được ghi trong một báo cáo bằng số báo cáo, support, xác suất có điều kiện và lift.",
        "run_a11",
    ),
    (
        "12_symptom_by_group.ipynb",
        "A12 — So sánh triệu chứng theo nhóm",
        "So sánh số lượng và phần trăm báo cáo có triệu chứng theo sản phẩm, hãng, dose series, tuổi, giới hoặc năm.",
        "run_a12",
    ),
]

workflow_names = {row[0] for row in WORKFLOWS}
if FRONTEND_NOTEBOOKS & BACKEND_NOTEBOOKS or FRONTEND_NOTEBOOKS | BACKEND_NOTEBOOKS != workflow_names:
    raise RuntimeError("Every workflow must be assigned to exactly one notebook layer")


def make_cell(kind: str, text: str) -> dict:
    cell = {
        "cell_type": kind,
        "id": uuid.uuid4().hex[:8],
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }
    if kind == "code":
        cell.update(execution_count=None, outputs=[])
    return cell


for filename, title, description, workflow in WORKFLOWS:
    layer = "frontend" if filename in FRONTEND_NOTEBOOKS else "backend"
    module_function = workflow
    notebook = {
        "cells": [
            make_cell(
                "markdown",
                f"# {title}\n\n{description}\n\n"
                "Notebook chỉ đọc PostgreSQL bằng role analyst. Chạy Restart Kernel and Run All "
                "để tái tạo. Kết quả CSV và hình được lưu vào analysis/reports.",
            ),
            make_cell(
                "markdown",
                "## Thiết lập và điều kiện dữ liệu\n\n"
                "Cài dependency một lần bằng lệnh py -m pip install -r "
                "analysis/requirements.txt. Notebook kết nối PostgreSQL local qua "
                "ANALYST_PASSWORD trong DVG6/.env. Nếu thiếu bảng hoặc bảng rỗng, workflow "
                "sẽ nêu điều kiện cần xử lý.",
            ),
            make_cell("code", SETUP),
            make_cell(
                "code",
                f"from analysis.eda_workflows import {module_function}\n"
                f"results = {module_function}()\n"
                "for result_name, result_frame in results.items():\n"
                "    print(result_name)\n"
                "    display(result_frame)",
            ),
        ],
        "metadata": {
            "dvg6": {"layer": layer, "workflow": workflow},
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    if filename == "08_cleaning_impact.ipynb":
        notebook["cells"].insert(
            1,
            make_cell(
                "markdown",
                "## Cách đọc box plot\n\n"
                "Đường giữa hộp là median; hai cạnh hộp là Q1 và Q3; whisker kéo đến các giá trị gần nhất nằm trong phạm vi 1.5 × IQR. "
                "Điểm ngoại lệ bị ẩn khỏi hình để dễ đọc, nhưng min/max vẫn có trong bảng CSV. "
                "Mỗi hàng là phân bố tuổi của các báo cáo riêng biệt có triệu chứng đó; một báo cáo có thể xuất hiện ở nhiều hàng triệu chứng.",
            ),
        )
    if filename == "09_onset_timing.ipynb":
        notebook["cells"][0] = make_cell(
            "markdown",
            "# A9 — Thời gian từ tiêm đến khởi phát\n\n"
            "Đo số ngày từ VAX_DATE đến ONSET_DATE ở cấp báo cáo. Mặc định chỉ tạo box plot top 5 triệu chứng. "
            "Nếu nhập một triệu chứng cụ thể ở ô cấu hình, workflow tạo thêm histogram cho triệu chứng đó.\n\n"
            "Lưu ý: VAERS không cho biết ngày khởi phát riêng cho từng symptom trong một báo cáo nhiều triệu chứng. "
            "Kết quả mô tả báo cáo VAERS, không phải thời gian khởi phát của quần thể hay quan hệ nhân quả.",
        )
        notebook["cells"][1] = make_cell(
            "markdown",
            "## Cách chọn chế độ\n\n"
            "Đặt `selected_symptom = None` để chỉ xem box plot top 5. Nhập tên symptom chuẩn, ví dụ `Headache`, "
            "để xem box plot top 5 và histogram riêng. Các ngày thiếu, không hợp lệ hoặc onset trước ngày tiêm bị loại.",
        )
        notebook["cells"][3] = make_cell(
            "code",
            "# None: chỉ box plot top 5. Ví dụ: selected_symptom = 'Headache'\n"
            "selected_symptom = None\n"
            "\n"
            "from analysis.eda_workflows import run_a9\n"
            "results = run_a9(selected_symptom=selected_symptom)\n"
            "for result_name, result_frame in results.items():\n"
            "    print(result_name)\n"
            "    display(result_frame)",
        )
    if filename == "10_outcomes_by_symptom.ipynb":
        notebook["cells"][0] = make_cell(
            "markdown",
            "# A10 — Cờ kết quả nghiêm trọng theo triệu chứng\n\n"
            "Heatmap biểu diễn phần trăm báo cáo có ghi cờ kết quả trong các báo cáo chứa từng triệu chứng. "
            "Mỗi ô cũng ghi số báo cáo có cờ / mẫu số báo cáo của triệu chứng. Các cờ có thể chồng lấp.\n\n"
            "Heatmap title states all vaccines when no vaccine filter is set; otherwise it displays the vaccine keyword used for a partial match.\n\n"
            "Đây là tỷ lệ trong tập báo cáo VAERS đang lọc, không phải nguy cơ trên người được tiêm hay kết luận nhân quả. "
            "Các cờ là thông tin được ghi trên báo cáo và có thể chưa được xác minh độc lập. Trong core, giá trị không phải Y (kể cả thiếu) thành false, nên mẫu số có thể gồm báo cáo không ghi rõ outcome.",
        )
        notebook["cells"][1] = make_cell(
            "markdown",
            "## Bộ lọc tùy chọn\n\n"
            "Nhập một phần tên sản phẩm trong `dim_vaccine.vax_name`, nhãn nhóm tuổi theo `dim_age_group`, "
            "và/hoặc khoảng `numdays` (ngày từ tiêm đến khởi phát). Để trống/đặt `None` để không lọc theo thuộc tính đó. "
            "Để `selected_symptom = None` xem top N theo cohort sau lọc; nhập symptom cụ thể để xem riêng triệu chứng đó, kể cả khi không nằm trong top N.",
        )
        notebook["cells"][3] = make_cell(
            "code",
            "from analysis.notebook_utils import query_df\n"
            "\n"
            "# Xem các giá trị có thể dùng trong bộ lọc\n"
            "display(query_df(\"SELECT DISTINCT dv.vax_name FROM core.dim_vaccine dv JOIN core.fct_report_vaccine rv ON rv.vaccine_key = dv.vaccine_key WHERE dv.vax_name <> 'UNKNOWN' ORDER BY 1\"))\n"
            "display(query_df(\"SELECT age_group_label FROM core.dim_age_group ORDER BY sort_order\"))\n"
            "\n"
            "vaccine_name = None  # từ khóa một phần, ví dụ: 'PFIZER'\n"
            "age_group = None     # ví dụ: '19-30'\n"
            "onset_min_days = None\n"
            "onset_max_days = None\n"
            "selected_symptom = None  # None: top N; enter a specific symptom\n"
            "top_n = 10\n"
            "\n"
            "from analysis.eda_workflows import run_a10\n"
            "results = run_a10(\n"
            "    vaccine_name=vaccine_name,\n"
            "    age_group=age_group,\n"
            "    onset_min_days=onset_min_days,\n"
            "    onset_max_days=onset_max_days,\n"
            "    selected_symptom=selected_symptom,\n"
            "    top_n=top_n,\n"
            ")\n"
            "for result_name, result_frame in results.items():\n"
            "    print(result_name)\n"
            "    display(result_frame)",
        )
    if filename == "11_symptom_cooccurrence.ipynb":
        notebook["cells"][0] = make_cell(
            "markdown",
            "# A11 — Các triệu chứng cùng xuất hiện\n\n"
            "Hai heatmap cho biết số báo cáo VAERS chứa đồng thời từng cặp triệu chứng và lift của cặp đó. "
            "Bảng CSV ghi số cặp báo cáo, support, P(B|A), P(A|B) và lift.\n\n"
            "Mỗi đơn vị là một báo cáo duy nhất. Đây là đồng đề cập trong báo cáo, không chứng minh triệu chứng này gây ra triệu chứng kia. "
            "Vì mỗi báo cáo có thể chứa nhiều triệu chứng, các xác suất có điều kiện không cần cộng thành 100%.",
        )
        notebook["cells"][1] = make_cell(
            "markdown",
            "## Tham số\n\n"
            "`top_n` chọn nhóm triệu chứng phổ biến nhất dùng trong hai heatmap. `min_pair_reports` chỉ lọc bảng cặp CSV; "
            "heatmap vẫn hiển thị toàn bộ nhóm đã chọn. Support lấy tổng số báo cáo phân biệt trong core làm mẫu số. "
            "Lift lớn hơn 1 nghĩa là cặp được ghi cùng nhau nhiều hơn mức kỳ vọng nếu độc lập trong tập báo cáo này.",
        )
        notebook["cells"][3] = make_cell(
            "code",
            "top_n = 10\n"
            "min_pair_reports = 1\n\n"
            "from analysis.eda_workflows import run_a11\n"
            "results = run_a11(top_n=top_n, min_pair_reports=min_pair_reports)\n"
            "for result_name, result_frame in results.items():\n"
            "    print(result_name)\n"
            "    display(result_frame)",
        )
    if filename == "12_symptom_by_group.ipynb":
        notebook["cells"][0] = make_cell(
            "markdown",
            "# A12 — So sánh triệu chứng theo nhóm người và vaccine\n\n"
            "Heatmap hiển thị phần trăm báo cáo trong mỗi nhóm có triệu chứng, kèm số báo cáo có triệu chứng / tổng số báo cáo của nhóm. "
            "Bảng CSV chứa các nhóm và top triệu chứng đầy đủ; hình giới hạn mỗi trục ở 10 nhóm lớn nhất và vẫn giữ UNKNOWN nếu có.\n\n"
            "Đây là phần trăm báo cáo VAERS, không phải tỷ lệ người tiêm mắc triệu chứng. Một báo cáo có thể thuộc nhiều nhóm sản phẩm/liều nếu ghi nhận nhiều vaccine.",
        )
        notebook["cells"][1] = make_cell(
            "markdown",
            "## Dimensions và cách đọc\n\n"
            "Có thể chọn hai dimension khác nhau: `product`, `manufacturer`, `dose_series`, `age_group`, `sex`, `report_year`. "
            "Nguồn chỉ có dose series, không có số thứ tự liều tiêm riêng cho từng sản phẩm. Missing/unspecified được giữ thành UNKNOWN. "
            "Mẫu số của mỗi ô là số report phân biệt thuộc nhóm đó; nếu nhóm theo vaccine, các nhóm có thể chồng lấp.",
        )
        notebook["cells"][3] = make_cell(
            "code",
            "group_by_x = 'age_group'  # product, manufacturer, dose_series, age_group, sex, report_year\n"
            "group_by_y = 'sex'\n"
            "selected_symptom = None  # None: top 10 CSV and top 5 panels; or exact symptom name\n"
            "top_n = 10\n\n"
            "from analysis.eda_workflows import run_a12\n"
            "results = run_a12(\n"
            "    group_by_x=group_by_x,\n"
            "    group_by_y=group_by_y,\n"
            "    selected_symptom=selected_symptom,\n"
            "    top_n=top_n,\n"
            ")\n"
            "for result_name, result_frame in results.items():\n"
            "    print(result_name)\n"
            "    display(result_frame)",
        )
    (NOTEBOOK_DIR / layer / filename).write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

print(f"Generated {len(FRONTEND_NOTEBOOKS)} frontend and {len(BACKEND_NOTEBOOKS)} backend notebooks in {NOTEBOOK_DIR}")
