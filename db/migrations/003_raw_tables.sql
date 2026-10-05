-- 003: bảng raw cho source_demo (nguồn giả, thay bằng nguồn thật ở M5).
-- Quy ước: cột nghiệp vụ là text, giữ nguyên trạng; 5 cột kỹ thuật bắt buộc ở mọi bảng raw.

create table raw.source_demo_records (
    record_id     text,
    entity_code   text,
    entity_name   text,
    category      text,
    event_date    text,
    measure_value text,
    -- cột kỹ thuật
    _batch_id     uuid        not null references meta.ingestion_batch (batch_id),
    _source_name  text        not null,
    _ingested_at  timestamptz not null default now(),
    _row_hash     text        not null,
    _payload      jsonb
);
-- Khử trùng lặp giữa các lô: cùng bản ghi gốc -> cùng hash -> ON CONFLICT DO NOTHING.
create unique index source_demo_records_row_hash_uq on raw.source_demo_records (_row_hash);
create index on raw.source_demo_records (_batch_id);

comment on table  raw.source_demo_records               is 'Nguồn giả sinh ngẫu nhiên có seed (ingestion/sources/source_demo.py). Mỗi dòng là một sự kiện đo của một thực thể.';
comment on column raw.source_demo_records.record_id     is 'Mã sự kiện do nguồn cấp. Có thể rỗng.';
comment on column raw.source_demo_records.entity_code   is 'Mã thực thể, có thể lẫn chữ thường và khoảng trắng.';
comment on column raw.source_demo_records.entity_name   is 'Tên thực thể như nguồn ghi.';
comment on column raw.source_demo_records.category      is 'Nhóm của thực thể (A/B/C/D), chưa chuẩn hóa hoa/thường.';
comment on column raw.source_demo_records.event_date    is 'Ngày sự kiện, dạng YYYY-MM-DD.';
comment on column raw.source_demo_records.measure_value is 'Độ đo dạng chuỗi số, có thể rỗng.';
comment on column raw.source_demo_records._batch_id     is 'Lô nạp sinh ra dòng này (meta.ingestion_batch).';
comment on column raw.source_demo_records._source_name  is 'Tên nguồn.';
comment on column raw.source_demo_records._ingested_at  is 'Thời điểm ghi vào raw.';
comment on column raw.source_demo_records._row_hash     is 'md5 của bản ghi gốc (JSON sắp khóa), dùng khử trùng lặp.';
comment on column raw.source_demo_records._payload      is 'Bản ghi gốc nguyên vẹn, phòng khi parse sai.';
