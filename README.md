# QTDL Warehouse — PostgreSQL warehouse + web dashboard

Warehouse PostgreSQL nhiều tầng (`raw → staging → core → analytics`, cộng `meta`) với ingestion có nhật ký lô, transform bằng dbt, cổng chất lượng tự động và dashboard React hiển thị cả kết quả phân tích lẫn sức khỏe dữ liệu.

**Trạng thái:** M1–M4 xong, chạy trên nguồn giả `source_demo`. Topic chưa chốt; M5 thay bằng nguồn thật.

| Mốc | Nội dung | Trạng thái |
|---|---|---|
| M1 | Khung, Docker, migration, CI | ✅ |
| M2 | Connector mẫu `source_demo` đi hết đường ống, idempotent | ✅ |
| M3 | dbt staging/core/analytics + quality gate (exit 1 khi hỏng) | ✅ |
| M4 | FastAPI + dashboard: Tổng quan, Sức khỏe pipeline, Catalog | ✅ |
| M5 | Nguồn thật | ⏳ chờ chốt topic |
| M6 | Phân tích, trang Khám phá + Phân tích | ⏳ |
| M7 | Tài liệu, báo cáo | ⏳ |

## Chạy

Máy chỉ cần **git, Docker (đang chạy), make**. Không cần cài Python/Node/Postgres. Windows: `winget install ezwinports.make`.

```bash
git clone https://github.com/nmdbbb/DVG6.git && cd DVG6
cp .env.example .env    # tùy chọn
make up && make migrate && make ingest && make transform && make quality
make dashboard          # http://localhost:5173 · API: http://localhost:8000/docs
```

| Lệnh | Việc |
|---|---|
| `make all` | up → migrate → ingest → transform → quality |
| `make reset` | xóa sạch warehouse rồi dựng lại từ số không |
| `make test` | pytest (API trên database thật) |
| `make lint` | ruff + black |
| `make lineage` | dbt docs + lineage graph, http://localhost:8080 |
| `make demo-break` | làm hỏng một dòng để thấy `make quality` chặn pipeline |
| `make psql` | mở psql |

Chi tiết và lỗi thường gặp: [docs/runbook.md](docs/runbook.md).

---

## Phân vai — mỗi người chọn một vai, điền tên vào cột "Người nhận"

Mỗi vai **sở hữu** một vùng thư mục: chỉ người giữ vai sửa vùng đó (Code Owners chặn merge nếu thiếu người duyệt, xem [.github/CODEOWNERS](.github/CODEOWNERS)). Cột "Để ý" là file của người khác mà thay đổi ở đó có thể làm vỡ phần của bạn: đọc, theo dõi PR, nhưng không sửa trực tiếp.

| # | Vai | Người nhận | Sửa (workspace của bạn) | Để ý (đọc, không sửa) | Xong khi |
|---|---|---|---|---|---|
| 1 | **Data Architect & Integration Owner** | _…_ | [db/migrations/](db/migrations/) · [db/roles.sql](db/roles.sql) · [db/seeds/](db/seeds/) · [scripts/](scripts/) · [common/](common/) · [docker-compose.yml](docker-compose.yml) · [Makefile](Makefile) · [.github/](.github/) · [docs/schema.md](docs/schema.md) · [docs/data_contract.md](docs/data_contract.md) · [docs/decision_log.md](docs/decision_log.md) · [docs/runbook.md](docs/runbook.md) | [transform/models/core/](transform/models/core/) (duyệt mọi PR) · [ingestion/base.py](ingestion/base.py) · [transform/dbt_project.yml](transform/dbt_project.yml) | Contract chốt; mỗi bảng core có grain; `make reset && make all` chạy sạch |
| 2 | **Data Acquisition** (2 người, mỗi người một nguồn) | _…_ · _…_ | [ingestion/sources/](ingestion/sources/)`<nguồn của bạn>.py` · [ingestion/registry.py](ingestion/registry.py) (thêm một dòng) · [ingestion/tests/](ingestion/tests/) · [docs/sources.md](docs/sources.md) (mục nguồn của bạn) | [ingestion/base.py](ingestion/base.py) · [ingestion/loader.py](ingestion/loader.py) · [db/migrations/003_raw_tables.sql](db/migrations/003_raw_tables.sql) (mẫu bảng raw — nhờ Architect viết migration cho nguồn mới) · [docs/data_contract.md](docs/data_contract.md) | `make ingest SOURCE=<nguồn>` chạy 2 lần, lần 2 ghi 0 dòng mới; bản gốc nằm ở `data/raw/<nguồn>/` |
| 3 | **Transform** | _…_ | [transform/models/staging/](transform/models/staging/) · [transform/models/core/](transform/models/core/) · [transform/models/analytics/](transform/models/analytics/) · [transform/macros/](transform/macros/) · [docs/cleaning_log.md](docs/cleaning_log.md) | Bảng `raw.*` (migration) · [quality/rules.yml](quality/rules.yml) · [api/routers/](api/routers/) (đang đọc view nào trong analytics) | `make transform && make quality` xanh; mỗi phép làm sạch có một dòng trong cleaning_log |
| 4 | **Analysis & Quality Owner** | _…_ | [quality/rules.yml](quality/rules.yml) · [quality/runner.py](quality/runner.py) · [quality/checks/](quality/checks/) · [analysis/notebooks/](analysis/notebooks/) · [analysis/reports/](analysis/reports/) · [docs/business_case.md](docs/business_case.md) | [transform/models/core/](transform/models/core/) (grain, cột) · `schema.yml` (dbt test) · [docs/cleaning_log.md](docs/cleaning_log.md) · [docs/quality_report.md](docs/quality_report.md) (sinh tự động) | Câu hỏi nghiên cứu chốt; ngưỡng chất lượng có lý do; mọi con số trong báo cáo tái tạo được từ warehouse |
| 5 | **Dashboard** | _…_ | [api/](api/) (`main.py`, `routers/`, `schemas/`, `tests/`) · [web/src/](web/src/) (`pages/`, `components/`, `api/client.ts`, `lib/`) · [web/package.json](web/package.json) | [transform/models/analytics/](transform/models/analytics/) (view bạn đọc) · bảng `meta.*` trong [db/migrations/](db/migrations/) · [db/roles.sql](db/roles.sql) (API chỉ đọc `analytics` + `meta`) | Mọi số trên dashboard đến từ API, không hard-code; mỗi endpoint có test; type sinh từ OpenAPI |

### Workspace từng vai — sửa ở đâu, để ý gì

<details>
<summary><b>1. Data Architect & Integration Owner</b></summary>

- **Đổi schema:** thêm file mới `db/migrations/00N_<việc>.sql`. **Không sửa file đã merge** — `scripts/migrate.py` so checksum và dừng nếu lệch.
- **Mọi bảng/cột mới phải có `COMMENT ON`** — trang Catalog đọc thẳng các comment này.
- **Thêm bảng raw cho nguồn mới:** theo mẫu `003_raw_tables.sql` (cột nghiệp vụ `text` + 5 cột kỹ thuật + unique index `_row_hash`).
- **Quyền:** `db/roles.sql` chạy lại sau mỗi `make migrate`. `etl_writer` chỉ được `INSERT` vào raw — giữ nguyên.
- **Duyệt:** mọi PR chạm `db/` và `transform/models/core/`.
- Mỗi quyết định có đánh đổi → một dòng trong `docs/decision_log.md`.
</details>

<details>
<summary><b>2. Data Acquisition</b></summary>

- Copy [ingestion/sources/source_demo.py](ingestion/sources/source_demo.py) thành `ingestion/sources/<nguồn>.py`, kế thừa `Connector` ([ingestion/base.py](ingestion/base.py)): khai báo `name`, `raw_table`, `columns`, viết `fetch()` và `describe()`.
- Đăng ký trong [ingestion/registry.py](ingestion/registry.py). **Không sửa** `loader.py`, `cli.py`, `base.py` — cần đổi thì mở issue cho Architect.
- **Không làm sạch trong connector:** không đổi tên cột, không ép kiểu, không lọc dòng. Trả về đúng chuỗi nguồn cho.
- Có API chính thức thì dùng API; scrape thì tôn trọng `robots.txt` và rate limit.
- Thử nhanh: `docker compose run --rm etl python -m ingestion.cli run --source <nguồn> --limit 100 --dry-run`.
- Điền mục nguồn của bạn trong [docs/sources.md](docs/sources.md) theo mẫu ở đầu file.
</details>

<details>
<summary><b>3. Transform</b></summary>

- **Staging** `stg_<nguồn>__<thực thể>.sql`: một model cho mỗi bảng raw, chỉ đổi tên, ép kiểu, trim, chuẩn hóa hoa/thường, lọc lô fail. Không join, không bỏ dòng.
- **Core** `dim_*.sql` / `fct_*.sql`: làm sạch thật. Dòng không map được dimension trỏ về `-1`, không để rơi khi join.
- **Analytics** `v_<câu hỏi>.sql`: một view cho mỗi biểu đồ.
- Mọi model có `description` cho bảng và từng cột trong `schema.yml` (dbt ghi thành `COMMENT ON`), test `unique`/`not_null`/`relationships` cho khóa.
- **Không có dòng trong [docs/cleaning_log.md](docs/cleaning_log.md) thì không merge.**
- Chạy một phần: `docker compose run --rm etl dbt run --select core.dim_entity+`.
</details>

<details>
<summary><b>4. Analysis & Quality Owner</b></summary>

- Check đơn giản (khóa, not null, quan hệ, tập giá trị) → khai báo trong `schema.yml` của dbt. Check phức tạp (đối chiếu số dòng giữa tầng, tỉ lệ, độ tươi) → [quality/rules.yml](quality/rules.yml): một câu SQL trả về một số + `expect`.
- `severity: error` chặn pipeline; `warning` chỉ báo. Đổi ngưỡng phải ghi lý do vào `decision_log.md`.
- Khi đổi nguồn ở M5: sửa `raw_to_core_row_reconciliation` trỏ đúng bảng raw mới.
- Notebook đọc từ `core`/`analytics` bằng role `analyst` (mật khẩu `ANALYST_PASSWORD`), **không đọc file rời**. Kết quả phân tích ghi vào bảng để API phục vụ.
- Duyệt mọi PR chạm `analysis/` hoặc kết luận thống kê. Vì bạn cũng viết notebook, PR `analysis/` của chính bạn cần một người khác review chéo.
</details>

<details>
<summary><b>5. Dashboard</b></summary>

- API chỉ đọc `analytics.*` và `meta.*` qua role `api_reader` ([api/deps.py](api/deps.py)). Cần dữ liệu từ core → nhờ Transform tạo view trong analytics.
- Mọi response bọc `{data, meta}` ([api/schemas/common.py](api/schemas/common.py)); tham số qua Pydantic + bind parameter, không nối chuỗi SQL.
- Mỗi endpoint một test trong [api/tests/](api/tests/), chạy trên database thật.
- Đổi API xong: `cd web && npm run gen:api` để sinh lại [web/src/api/schema.d.ts](web/src/api/schema.d.ts). Không gõ tay interface.
- Mỗi biểu đồ đặt trong `ChartCard` (hiện `as_of` + nguồn, nút Tải CSV). Bộ lọc dùng `FilterBar` (lưu trên URL).
- Endpoint M6 đã có chỗ: [api/routers/explore.py](api/routers/explore.py), [api/routers/analysis.py](api/routers/analysis.py).
</details>

---

## Quy trình Git

- `main` được bảo vệ: chỉ nhận qua pull request, cần 1 approve của Code Owner và CI `lint` + `pipeline` xanh.
- Nhánh đặt tên `<vai>/<việc>`: `ingest/source-a`, `core/dim-entity`, `web/overview-page`, `db/raw-source-a`.
- Một PR một việc. Checklist merge nằm trong PR template.
- **Không commit** `data/` và `.env` (đã chặn trong `.gitignore` và CI).

## Cấu trúc

```
db/            migration, role, seed           ← Architect
ingestion/     connector, loader, CLI          ← Acquisition
transform/     dbt: staging, core, analytics   ← Transform
quality/       rules.yml, runner               ← Analysis & Quality
analysis/      notebook, report                ← Analysis & Quality
api/           FastAPI                         ← Dashboard
web/           React + Vite + ECharts          ← Dashboard
docs/          contract, log, runbook          ← mỗi file một chủ (xem bảng trên)
scripts/       migrate, reset, demo_break      ← Architect
common/        kết nối DB dùng chung           ← Architect
data/          KHÔNG commit (raw gốc, export)
```

Tài liệu: [schema](docs/schema.md) · [data contract](docs/data_contract.md) · [nguồn](docs/sources.md) · [decision log](docs/decision_log.md) · [cleaning log](docs/cleaning_log.md) · [quality report](docs/quality_report.md) · [runbook](docs/runbook.md) · [business case](docs/business_case.md)
