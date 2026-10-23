# Kho dữ liệu dùng chung

Nhóm có **hai nơi chứa dữ liệu**, đừng nhầm lẫn giữa chúng.

| | Warehouse local | Kho dùng chung |
|---|---|---|
| Ở đâu | Docker trên máy mỗi người | Neon (Postgres trên mạng) |
| Dùng để | làm việc: ingest, transform, sửa model, chạy quality | đọc kết quả: notebook, dashboard, báo cáo |
| Có schema nào | `raw`, `staging`, `core`, `analytics`, `meta` | `core`, `analytics`, `meta` |
| Ai ghi được | chính người đó | **chỉ** `make publish` |
| Hỏng thì sao | `make reset` dựng lại, không ảnh hưởng ai | publish lại từ một máy local |

Kho chung là **bản sao chỉ-đọc** của warehouse local, không phải nơi tích lũy dữ liệu riêng. Mỗi
lần publish thay toàn bộ ba schema. Quyết định: [decision_log](decision_log.md) #35–37.

## Kho này **không** giải quyết việc chia sẻ file nguồn

Kho chung chứa **kết quả đã làm sạch**. Nó không chứa `raw`, nên không giúp người viết model
transform có dữ liệu để làm việc. Hai nhu cầu khác nhau, hai cơ chế khác nhau:

| Nhu cầu | Cơ chế |
|---|---|
| Cả nhóm xem cùng một kết quả đã làm sạch | kho Postgres này |
| Cả nhóm chạy được pipeline từ cùng một file nguồn | **GitHub Release** + `make landing-fetch` |

Nguồn phải tải tay (VAERS có CAPTCHA) lại được dựng lại định kỳ ở phía CDC, nên mỗi người tự tải
sẽ ra file khác nhau và `make landing-verify` sẽ chặn. Vì vậy một người tải, đẩy lên Release bằng
`make landing-upload`, cả nhóm lấy đúng bản đó bằng `make landing-fetch`. Chi tiết:
[runbook](runbook.md) mục "Nguồn tải tay".

## Kho hiện tại

| | |
|---|---|
| Nhà cung cấp | [Neon](https://neon.com), gói miễn phí |
| Project | `DVG6`, branch `production` |
| Region | `ap-southeast-1` (Singapore) |
| PostgreSQL | 18 |
| Database | `neondb` |
| Tài khoản | đăng nhập bằng GitHub `nmdbbb` — Data Architect giữ |
| Hạn mức | 500 MB |
| Đang dùng | 8,6 MB (2026-10-23, còn là dữ liệu giả `source_demo`) |

## Trên kho có gì, và vì sao thiếu những cái kia

**Có:**

| Schema | Nội dung | Ai cần |
|---|---|---|
| `core` | star schema đã làm sạch: `dim_*`, `fct_*` | Analysis (notebook) |
| `analytics` | view `v_*` tổng hợp sẵn cho từng biểu đồ | Dashboard |
| `meta` | nhật ký lô nạp, kết quả quality, profile bảng | Dashboard (trang Sức khỏe pipeline, Catalog) |

**Không có, và lý do:**

- **`raw`** — với VAERS, cột `SYMPTOM_TEXT` cộng cột `_payload` làm schema này nặng hơn 1 GB, vượt
  hạn mức 500 MB. Muốn truy vết một dòng `core` ngược về `raw` thì phải làm trên máy đã chạy ingest.
- **`staging`** — chỉ là view dựng lại được từ `raw`, không có giá trị riêng.
- **`meta.ingestion_batch_row`** — một dòng cho mỗi bản ghi mỗi lô, với VAERS là vài triệu dòng.
  Chỉ `make mock-check` ở local dùng tới, dashboard không đụng đến.

## Kết nối vào kho

Ba role, mỗi role chỉ thấy đúng phần mình cần. Mật khẩu xin Data Architect, **gửi riêng** —
không đưa vào repo, issue hay nhóm chat chung.

| Role | Đọc được | Dùng cho |
|---|---|---|
| `analyst` | `core`, `analytics` | notebook phân tích |
| `api_reader` | `analytics`, `meta` | API của dashboard |
| `neondb_owner` | tất cả, ghi được | chỉ Data Architect, chỉ để publish |

### Notebook (role `analyst`)

```python
import os

import polars as pl
import psycopg

# Đặt biến môi trường, đừng viết mật khẩu thẳng vào notebook rồi commit.
with psycopg.connect(os.environ["ANALYST_DATABASE_URL"]) as conn:
    df = pl.read_database("select * from core.fct_report_symptom limit 1000", conn)
```

Dùng `pl.read_database` với một kết nối `psycopg`, **không** dùng `pl.read_database_uri` —
hàm đó đòi thư viện `connectorx` mà repo không cài.

Chuỗi kết nối có dạng:

```
postgresql://analyst:<mật khẩu>@ep-wispy-mountain-a107bn9j-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

`sslmode=require` là **bắt buộc**, Neon từ chối kết nối không mã hóa.

### Dashboard (role `api_reader`)

Đặt `API_DATABASE_URL` trong `.env` rồi chạy API như bình thường:

```
API_DATABASE_URL=postgresql://api_reader:<mật khẩu>@ep-....aws.neon.tech/neondb?sslmode=require
```

Để trống thì API đọc Postgres local — đây là mặc định khi dev, và nên giữ như vậy lúc đang sửa code.

### psql

```bash
docker compose run --rm etl sh -c 'psql "$SHARED_DATABASE_URL"'
```

Nháy đơn là cố ý: biến nằm trong container chứ không phải ở máy bạn, nên phải để shell trong
container tự thay giá trị.

## Đưa dữ liệu lên kho

**Ai:** Data Architect. **Khi nào:** sau khi `make quality` xanh ở local.

```bash
make publish DRY_RUN=1   # xem sẽ đẩy bảng nào, bao nhiêu dòng — không ghi gì
make publish             # đẩy thật
```

Publish dữ liệu chưa qua quality gate là đưa số sai cho cả nhóm. Lệnh không tự kiểm điều này —
đây là kỷ luật của người chạy.

Lệnh làm bốn việc: `pg_dump` ba schema từ local, xóa ba schema cũ trên kho chung, nạp bản mới, cấp
lại quyền cho `analyst` và `api_reader`. Xong thì **tự so số dòng từng bảng hai bên** và exit 1 nếu
lệch, nên không có chuyện publish nửa vời mà tưởng là xong.

Không cần `make migrate` trên kho chung: bản dump mang sẵn cả cấu trúc lẫn dữ liệu.

**Nhớ publish lại sau mỗi lần pipeline đổi.** Không có gì tự động nhắc; kho chung cũ hơn local là
lỗi âm thầm khó phát hiện nhất của cách làm này.

## Chốt chặn an toàn

- `make migrate`, `make ingest`, `make quality`, `make reset` **từ chối chạy** nếu `POSTGRES_HOST`
  không phải host local. Không ai lỡ tay xóa sạch dữ liệu cả nhóm bằng `make reset`.
- `make publish` từ chối nếu `SHARED_DATABASE_URL` lại trỏ vào host local.
- CI kiểm cả hai chiều này mỗi lần có pull request.
- `SHARED_DATABASE_URL` chứa mật khẩu nên chỉ nằm trong `.env`, vốn đã bị `.gitignore` chặn.

## Dung lượng

Hạn mức 500 MB. Ước tính khi có VAERS thật: `core` khoảng 200–300 MB.

Xem dung lượng đang dùng:

```sql
select pg_size_pretty(pg_database_size(current_database()));
```

**Vượt 400 MB thì dừng lại và bàn**, đừng đợi đụng trần. Ba hướng xử lý: thu hẹp phạm vi dữ liệu,
bỏ bớt cột không dùng trong `core`, hoặc trả tiền (Neon Launch khoảng 19 USD/tháng). Chọn hướng nào
cũng phải ghi một dòng vào [decision_log](decision_log.md).

## Lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Thiếu SHARED_DATABASE_URL` | chưa đặt biến trong `.env` | xin Data Architect connection string |
| `TỪ CHỐI: SHARED_DATABASE_URL trỏ vào host local` | dán nhầm chuỗi của Postgres local | dùng chuỗi Neon |
| `TỪ CHỐI: ... chỉ được chạy trên warehouse local` | `POSTGRES_HOST` đang trỏ ra Neon | trả `POSTGRES_HOST` về `localhost` |
| `LỆCH giữa local và kho chung` | publish đứt giữa chừng | chạy lại `make publish` |
| `unrecognized configuration parameter "transaction_timeout"` | kho chung chạy PostgreSQL dưới 17 | đã xử lý sẵn, lệnh tự bỏ dòng đó; nếu vẫn gặp thì báo Data Architect |
| `connection is insecure` | thiếu `sslmode=require` | thêm vào cuối chuỗi kết nối |
| Dashboard hiện số cũ | quên publish sau khi đổi pipeline | `make publish` |

## Đổi mật khẩu

Khi một mật khẩu lộ ra ngoài `.env` — gửi nhầm vào nhóm chat, dán vào issue, đưa cho công cụ ngoài:

1. **`neondb_owner`:** Neon console → branch `production` → Roles → Reset password. Rồi cập nhật
   `SHARED_DATABASE_URL` trong `.env` của người publish.
2. **`analyst` hoặc `api_reader`:** đổi giá trị tương ứng trong `.env` của người publish rồi chạy
   `make publish` — lệnh đặt lại mật khẩu trên kho chung mỗi lần chạy. Báo lại cho người đang dùng.

---

Liên quan: [runbook](runbook.md) · [data_contract](data_contract.md) §7 · [schema](schema.md) ·
[decision_log](decision_log.md) #35–39
