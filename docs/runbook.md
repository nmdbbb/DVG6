# Runbook

## Yêu cầu máy

- git
- Docker Desktop (Windows/macOS) hoặc Docker Engine + Compose v2 (Linux), đang chạy
- GNU make
  - Windows: `winget install ezwinports.make` rồi mở terminal mới
  - macOS: có sẵn (Xcode CLT) · Linux: `apt install make`
- **Đĩa trống ≥ 12 GB** và **RAM cấp cho Docker ≥ 4 GB**. Đo thực tế ở lần nghiệm thu
  2026-11-19 (xem mục dưới): image Docker ~2 GB, `data/landing/` 302 MB, `data/raw/` 1,8 GB,
  volume `pgdata` ~4,1 GB (`raw` 3,0 GB + `meta` 662 MB + `core` 379 MB).

Không cần cài Python, Node hay Postgres trên máy: mọi thứ chạy trong container.

## Dựng từ số không

```bash
git clone https://github.com/nmdbbb/DVG6.git && cd DVG6
cp .env.example .env          # tùy chọn: thiếu .env thì dùng mật khẩu mặc định change_me
make up && make migrate && make ingest && make transform && make quality
make dashboard                # http://localhost:5173 · API docs http://localhost:8000/docs
```

`make all` = up → migrate → ingest → transform → quality. Lần đầu mất vài phút để build image.

Chứng minh tái tạo được: `make reset` xóa sạch mọi schema rồi chạy lại toàn bộ.

## Nguồn tải tay (VAERS)

Trang tải của CDC có CAPTCHA nên **không** tự động hóa việc tải (decision #23). Mỗi người dựng lại warehouse làm như sau:

1. `make landing-fetch` — tải file từ GitHub Release của repo về `data/landing/`, tự kiểm sha256.
   Đây là cách **mặc định**: nguồn gốc cập nhật định kỳ nên mỗi người tự vào tải sẽ ra file khác
   nhau. Chỉ người tải tay lần đầu mới làm bước 3 bên dưới.
2. `make landing-verify` — in `Landing: N file khớp checksum`. Lệch hoặc thiếu file thì exit 1 kèm sha256 đúng cần tải.
3. Chỉ người **tải tay lần đầu** (hoặc khi nguồn đổi dữ liệu): đặt file vào
   `data/landing/<nguồn>/<ngày>/`, chạy `make landing-register SOURCE=vaers` (đặt `BY="Tên"` nếu
   không muốn lấy `git config user.name`) rồi `make landing-upload SOURCE=vaers` để đưa lên
   Release cho cả nhóm. Commit `sources_landing.md` cùng một dòng mới trong `decision_log.md`.
   File đổi nội dung thì thêm dòng mới, không sửa dòng cũ.

`make ingest` luôn chạy `landing-verify` trước, nên file bị sửa dù một byte cũng không được nạp.

## Từng bước làm gì

| Lệnh | Việc | Kiểm tra thành công |
|---|---|---|
| `make up` | Postgres 16 + mock_server chạy, chờ healthy; build image `qtdl/python:dev` | `docker compose ps` thấy `db`, `mock_server` healthy |
| `make migrate` | Chạy migration chưa áp dụng, cấp quyền theo `db/roles.sql` | in `Migration xong`; `meta.schema_version` có đủ số dòng bằng số file trong `db/migrations/` |
| `make landing-verify` | Băm lại mọi file trong `data/landing/` đã đăng ký, so với `sources_landing.md` | `Landing: N file khớp checksum`, exit 0 |
| `make ingest` | Mọi connector → `raw` + `meta.ingestion_batch`, đường `live`; lưu bản gốc ở `data/raw/` | dòng `live success`; chạy lại thì `new_rows=0` |
| `make ingest SOURCE_MODE=mock` | Như trên nhưng lấy từ mock_server | dòng `mock success` |
| `make mock-check` | live rồi mock cho `source_demo`, so hai lô | in `KHỚP`, exit 0 |
| `make transform` | `dbt run`: staging → core → analytics | `PASS=21 ERROR=0` (đủ cả VAERS; chỉ có `source_demo` thì ít hơn) |
| `make quality` | `dbt test` + `quality/rules.yml`, ghi `meta.quality_run`, profile bảng, sinh `docs/quality_report.md` | `Quality gate passed.`, exit 0 |
| `make test` | pytest (API trên database thật, ingestion, mock server) | `passed` |
| `make demo-break` | Chèn một dòng mồ côi vào `core.fct_main` | `make quality` sau đó phải exit 1; `make transform` để sửa |
| `make publish` | Đẩy `core` + `analytics` + `meta` lên kho dùng chung | in `KHỚP: N bảng, M dòng`, exit 0 |

## Nghiệm thu tái tạo trên dữ liệu VAERS thật (issue #34)

Số đo của lần nghiệm thu **2026-11-19**: Windows 11, Docker Desktop 29.1.3, Docker được cấp
7,75 GB RAM, SSD, mạng gia đình. Máy khác sẽ lệch, nhưng thứ tự độ lớn giữ nguyên — dùng bảng này
để biết một bước đang chạy bình thường hay đã treo.

| Bước | Thời gian | Ghi chú |
|---|---|---|
| `make up` | 60 s | lần đầu build image `qtdl/python:dev`; lần sau vài giây |
| `make landing-fetch` | 57 s | 6 file VAERS, 302 MB, từ GitHub Release |
| `make migrate` | 2 s | 7 migration |
| `make landing-verify` | 4 s | băm lại 302 MB |
| `make ingest` | **17 phút** | openfda 138 s · source_demo 1 s · vaers_data 371 s · vaers_symptoms 304 s · vaers_vax 192 s |
| `make transform` | 88 s | 21 model (15 bảng, 6 view) |
| `make quality` | 51 s | 137 check, 0 error, 0 warning |
| `make test` | 5 s | 65 test |

Nghiệm thu chính thức — `make reset` (xóa sạch schema → migrate → ingest → transform → quality) chạy
**947 giây ≈ 15 phút 47 giây, exit 0**. Cộng `make up` lần đầu và `make landing-fetch` thì một người
mới clone repo mất **khoảng 18 phút** để có warehouse đầy đủ. Chạy tiếp `make all` ngay sau đó:
**784 giây, exit 0**, và ingest báo `new_rows=0` cho cả 5 nguồn — nạp lại không nhân dòng nào, số
dòng mọi bảng không đổi.

Ingest chiếm hơn 80% thời gian đó, và chậm vì mỗi dòng raw còn lưu thêm bản ghi gốc vào `_payload`
(JSONB) ngoài các cột text: riêng openFDA tải 990 MB phản hồi API cho 26 000 dòng.

### Số dòng phải ra đúng

Nạp đúng bộ file trong `sources_landing.md` thì các con số này tái tạo được nguyên vẹn:

| Bảng | Số dòng |
|---|---|
| `raw.vaers_data` · `raw.vaers_symptoms` · `raw.vaers_vax` | 768 704 · 1 030 201 · 811 756 |
| `raw.openfda_substances` · `raw.source_demo_records` | 26 000 · 5 000 |
| `staging.stg_vaers__symptoms` (sau unpivot) | 3 263 884 |
| `staging.stg_openfda__substances` | 3 885 |
| `core.dim_symptom` · `dim_vaccine` · `dim_state` · `dim_age_group` · `dim_sex` · `dim_date` | 11 197 · 142 · 63 · 8 · 3 · 2 193 |
| `core.fct_report_raw` | 711 058 |
| `core.report_duplicate_map` | 23 671 |
| `core.fct_report` | 687 387 |
| `core.fct_report_symptom` · `core.fct_report_vaccine` | 3 062 197 · 717 541 |

`raw.vaers_vax` nhận 813 432 dòng nhưng chỉ còn **811 756**: 1 676 dòng trùng y hệt trong CSV nguồn
bị `_row_hash` khử — đúng thiết kế, không phải mất dữ liệu.

**Hai bảng dị ứng thì chưa tái tạo được:** `core.dim_allergen` và `core.fct_report_allergen` phụ
thuộc từ điển hoạt chất openFDA, mà nguồn này crawl **live** mỗi lần `make ingest` nên đổi theo
ngày. Lần nghiệm thu này ra 1 222 và 272 636, trong khi `cleaning_log.md` hàng 14/20 ghi 1 217 và
272 841 (lệch 5 hoạt chất và 205 cặp). Chỉ VAERS đang được ghim bằng sha256; openFDA chưa — xem
issue #57.

## Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `failed to connect to the docker API` | Docker Desktop chưa chạy | Mở Docker Desktop, chờ "Engine running" |
| `make: command not found` | chưa cài make / terminal cũ | cài make (mục trên), mở terminal mới |
| `port is already allocated` (5432/8000/5173/8001) | máy đã có Postgres/app khác | đổi `POSTGRES_PORT`/`API_PORT`/`WEB_PORT`/`MOCK_PORT` trong `.env` |
| mock: `503 Chưa có snapshot live` | chưa có lô live hoàn chỉnh trong `data/raw/<source>/` | `make ingest SOURCE_MODE=live` trước |
| mock: `sha256 lệch` | file trong `data/raw/` bị sửa tay | không sửa bản gốc; chạy lại live để có snapshot mới |
| mock: `không lọc --since` | dùng `--since` với mock | chạy live với `--since`, sau đó mock phát lại snapshot đó |
| mock chậm | đúng thiết kế: trễ 200–500 ms, 60 request/phút | tăng `mock_page_size` của connector (JSON), hoặc giảm độ trễ trong `.env` khi chạy thử |
| `Checksum lệch` khi `make landing-verify` / `make ingest` | file trong `data/landing/` bị sửa hoặc tải nhầm bản | tải lại đúng file theo sha256 trong `sources_landing.md`; chỉ khi chủ ý đổi dữ liệu mới `make landing-register` và ghi `decision_log.md` |
| `checksum lệch` khi migrate | ai đó sửa file migration đã áp dụng | hoàn tác file đó, viết migration mới số lớn hơn |
| `password authentication failed for user "etl_writer"` | đổi mật khẩu trong `.env` sau khi đã migrate | `make migrate` (cập nhật lại mật khẩu role) |
| `relation "core.fct_main" does not exist` khi quality | chưa transform | `make transform` |
| `QUALITY GATE FAILED` | có check `error` fail | đọc `docs/quality_report.md` hoặc trang Pipeline health; sửa dữ liệu/model, không nới ngưỡng nếu chưa ghi `decision_log.md` |
| `make transform` đứng hàng chục phút ở một model `core` (gặp thật ở `report_duplicate_map`) | bảng vừa được dbt tạo chưa có thống kê, planner tưởng bảng rỗng và chọn kế hoạch sai; autovacuum chạy sau cũng không lập lại kế hoạch | kiểm `+post-hook: "analyze {{ this }}"` còn trong `transform/dbt_project.yml` mục `core` (decision #43). Đo thực tế: thiếu dòng này 73 phút chưa xong, có thì 10,6 giây |
| Số dòng `dim_allergen` / `fct_report_allergen` lệch `cleaning_log.md` | từ điển openFDA crawl live nên đổi theo ngày | bình thường, không phải lỗi; xem mục nghiệm thu ở trên và issue #57 |
| Đĩa đầy giữa `make ingest` | một vòng đầy cần ~12 GB (xem Yêu cầu máy) | dọn chỗ rồi `make reset`; `docker builder prune` lấy lại được vài GB cache build |
| `du` của `data/raw/` phình sau nhiều lần ingest | mỗi lô live lưu một snapshot mới, snapshot cũ giữ nguyên làm bằng chứng | xóa tay thư mục lô cũ trong `data/raw/<nguồn>/<ngày>/`; đừng xóa lô đang được mock phát lại |
| Dashboard trắng / lỗi API | api chưa chạy | `make dashboard`, `make logs` để xem log |

## Thao tác khác

- `make psql` — mở psql với tài khoản admin
- `make lineage` — dbt docs + lineage graph tại http://localhost:8080
- `docker compose --profile tools up -d pgadmin` — pgAdmin tại http://localhost:5050
- `make down` — dừng mọi container (dữ liệu giữ trong volume `pgdata`); `docker compose down -v` để xóa luôn volume
- Sinh lại type cho frontend sau khi đổi API: `make dashboard` rồi `cd web && npm run gen:api`

## Kho Postgres dùng chung

Warehouse local là nơi làm việc; kho dùng chung (Neon) là bản sao chỉ-đọc của `core`, `analytics`,
`meta` để cả nhóm và dashboard nhìn cùng một số liệu.

```bash
make publish DRY_RUN=1   # xem sẽ đẩy gì, không ghi
make publish             # đẩy thật, sau khi make quality xanh
```

Chi tiết đầy đủ — thông tin kho, cách kết nối cho từng role, hạn mức, lỗi thường gặp, cách đổi mật
khẩu — ở **[kho_du_lieu.md](kho_du_lieu.md)**.

## Branch protection

`main` chỉ nhận qua pull request, cần 1 approve và CI `lint` + `pipeline` xanh; PR chạm `db/`, `transform/models/`, `analysis/` cần thêm approve của Code Owner (`.github/CODEOWNERS`). Chủ repo đang được bypass để không bị khóa khi nhóm chưa vào đủ. Khi cả nhóm đã là collaborator:

```bash
gh api -X POST repos/nmdbbb/DVG6/branches/main/protection/enforce_admins
```

## Đường dự phòng mock_server

Nguồn thật là đường chính. Khi nguồn thật chậm, bị chặn, đổi cấu trúc, hoặc cần chạy lại pipeline nhiều lần:

```bash
make ingest SOURCE_MODE=mock              # hoặc đặt SOURCE_MODE=mock trong .env
docker compose run --rm etl python -m ingestion.cli run --source source_demo --endpoint mock
```

- Mock phát lại snapshot live **hoàn chỉnh mới nhất** của từng nguồn (`data/raw/<source>/<ngày>/<batch_id>/manifest.json`). Xem nguồn nào đang có snapshot: http://localhost:8001 hoặc `docker compose run --rm etl python -m mock_server.seed`.
- HTML: `http://localhost:8001/<source>?page=N` (20 dòng/trang, `<a rel="next">`). JSON: `http://localhost:8001/api/<source>?page=N&page_size=M` (cùng hình dạng API thật, `page_size` tối đa 1000). Cả hai có header `Link: rel="next"` và `X-Mock-Snapshot`.
- Điều kiện mô phỏng: trễ 200–500 ms mỗi request; quá 60 request/phút/client trả `429` kèm `Retry-After` (`http_client` tự chờ và thử lại). `/health` không tính.
- Nghiệm thu: `make mock-check` chạy `scripts/compare_batches.py` so lô live và lô mock mới nhất: cùng `rows_fetched`, cùng tập `_row_hash` (bảng `meta.ingestion_batch_row`), mọi hash đều có trong raw.
