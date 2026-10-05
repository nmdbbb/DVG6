-- 005: hai đường lấy dữ liệu — live (nguồn thật, đường chính) và mock (mock_server phát lại
-- bản gốc đã lưu ở data/raw, đường dự phòng) — cộng vết nội dung của từng lô.

alter table meta.ingestion_batch
    add column source_mode text not null default 'live'
        check (source_mode in ('live', 'mock'));
comment on column meta.ingestion_batch.source_mode is
    'live = lấy từ nguồn thật; mock = lấy từ mock_server phát lại bản gốc của một lô live trước đó.';

-- raw khử trùng lặp theo _row_hash, nên lô chạy lại (hoặc lô mock) ghi 0 dòng mới vào raw.
-- Bảng này giữ danh sách bản ghi MỖI LÔ đã thấy, để so hai lô với nhau và truy vết đầy đủ.
create table meta.ingestion_batch_row (
    batch_id  uuid not null references meta.ingestion_batch (batch_id),
    row_hash  text not null,
    primary key (batch_id, row_hash)
);
create index on meta.ingestion_batch_row (row_hash);
comment on table  meta.ingestion_batch_row          is 'Mỗi _row_hash mà một lô nạp đã lấy về, kể cả bản ghi đã có sẵn trong raw. Dùng so khớp lô live và lô mock (scripts/compare_batches.py).';
comment on column meta.ingestion_batch_row.batch_id is 'Lô nạp.';
comment on column meta.ingestion_batch_row.row_hash is 'Khớp raw.<bảng>._row_hash.';
