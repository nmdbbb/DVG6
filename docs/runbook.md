# Runbook

## Yêu cầu máy

- git
- Docker Desktop (Windows/macOS) hoặc Docker Engine + Compose v2 (Linux), đang chạy
- GNU make
  - Windows: `winget install ezwinports.make` rồi mở terminal mới
  - macOS: có sẵn (Xcode CLT) · Linux: `apt install make`

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
| `make transform` | `dbt run`: staging → core → analytics | `PASS=4 ERROR=0` |
| `make quality` | `dbt test` + `quality/rules.yml`, ghi `meta.quality_run`, profile bảng, sinh `docs/quality_report.md` | `Quality gate passed.`, exit 0 |
| `make test` | pytest (API trên database thật, ingestion, mock server) | `passed` |
| `make demo-break` | Chèn một dòng mồ côi vào `core.fct_main` | `make quality` sau đó phải exit 1; `make transform` để sửa |
| `make publish` | Đẩy `core` + `analytics` + `meta` lên kho dùng chung | in `KHỚP: N bảng, M dòng`, exit 0 |

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
