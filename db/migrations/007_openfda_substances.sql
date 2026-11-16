-- 007: bảng raw cho từ điển hoạt chất openFDA (ingestion/sources/openfda.py).
-- Tách khỏi 006 (3 bảng VAERS) để mỗi migration thuộc một người viết connector.
-- Cột nghiệp vụ là text, giữ nguyên trạng; 5 cột kỹ thuật bắt buộc như mọi bảng raw.

create table raw.openfda_substances (
    spl_id         text,
    substance_name text,
    rxcui          text,
    _batch_id      uuid        not null references meta.ingestion_batch (batch_id),
    _source_name   text        not null,
    _ingested_at   timestamptz not null default now(),
    _row_hash      text        not null,
    _payload       jsonb
);

create unique index openfda_substances_row_hash_uq on raw.openfda_substances (_row_hash);
create index on raw.openfda_substances (_batch_id);

comment on table  raw.openfda_substances                is 'Từ điển tên hoạt chất trích từ nhãn thuốc openFDA (api.fda.gov/drug/label). Một dòng cho mỗi nhãn có openfda.substance_name; dùng chuẩn hóa cột ALLERGIES của VAERS, không phải dữ liệu vắc xin.';
comment on column raw.openfda_substances.spl_id         is 'Mã SPL của nhãn (openfda.spl_id, phần tử đầu). Có thể rỗng; khi rỗng _row_hash tính từ cả nhãn gốc.';
comment on column raw.openfda_substances.substance_name is 'Mảng JSON (dạng chuỗi) các tên hoạt chất như openFDA trả về, chưa viết thường hay tách phần tử.';
comment on column raw.openfda_substances.rxcui          is 'Mảng JSON (dạng chuỗi) các mã RxCUI; NULL khi nhãn không có.';
comment on column raw.openfda_substances._batch_id      is 'Lô nạp sinh ra dòng này (meta.ingestion_batch).';
comment on column raw.openfda_substances._source_name   is 'Tên nguồn (openfda).';
comment on column raw.openfda_substances._ingested_at   is 'Thời điểm ghi vào raw.';
comment on column raw.openfda_substances._row_hash      is 'md5 của spl_id (hoặc của cả nhãn gốc nếu thiếu spl_id), dùng khử trùng lặp.';
comment on column raw.openfda_substances._payload       is 'Nhãn thuốc gốc nguyên vẹn từ openFDA, phòng khi parse sai.';
