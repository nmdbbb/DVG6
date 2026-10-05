-- 002: bảng nhật ký vận hành pipeline.

create table meta.source (
    source_name      text primary key,
    description      text,
    url              text,
    license          text,
    update_frequency text,
    owner            text,
    registered_at    timestamptz not null default now()
);
comment on table  meta.source                  is 'Danh mục nguồn dữ liệu. Mỗi connector tự đăng ký (ingestion/base.py: describe()).';
comment on column meta.source.source_name      is 'Khóa nguồn, khớp Connector.name.';
comment on column meta.source.description      is 'Mô tả ngắn nguồn chứa gì.';
comment on column meta.source.url              is 'Địa chỉ gốc của nguồn.';
comment on column meta.source.license          is 'Giấy phép sử dụng dữ liệu.';
comment on column meta.source.update_frequency is 'Tần suất nguồn cập nhật (daily, monthly, ...).';
comment on column meta.source.owner            is 'Người trong nhóm phụ trách connector.';
comment on column meta.source.registered_at    is 'Lần đầu nguồn được đăng ký.';

create table meta.ingestion_batch (
    batch_id      uuid primary key,
    source_name   text not null references meta.source (source_name),
    started_at    timestamptz not null default now(),
    finished_at   timestamptz,
    status        text not null check (status in ('running', 'success', 'failed')),
    rows_fetched  bigint,
    row_count     bigint,
    bytes         bigint,
    params        jsonb,
    error_message text
);
create index on meta.ingestion_batch (source_name, started_at desc);
comment on table  meta.ingestion_batch               is 'Một dòng cho mỗi lần chạy connector. Tầng staging chỉ lấy dòng raw thuộc lô success.';
comment on column meta.ingestion_batch.batch_id      is 'Định danh lô, trỏ từ cột _batch_id của mọi bảng raw.';
comment on column meta.ingestion_batch.source_name   is 'Nguồn của lô.';
comment on column meta.ingestion_batch.started_at    is 'Thời điểm bắt đầu nạp.';
comment on column meta.ingestion_batch.finished_at   is 'Thời điểm kết thúc (NULL khi đang chạy hoặc bị ngắt).';
comment on column meta.ingestion_batch.status        is 'running | success | failed.';
comment on column meta.ingestion_batch.rows_fetched  is 'Số bản ghi connector trả về.';
comment on column meta.ingestion_batch.row_count     is 'Số bản ghi mới thực sự ghi vào raw (sau khử trùng lặp theo _row_hash).';
comment on column meta.ingestion_batch.bytes         is 'Dung lượng bản gốc lưu ở data/raw.';
comment on column meta.ingestion_batch.params        is 'Tham số chạy (since, limit) để tái tạo lô.';
comment on column meta.ingestion_batch.error_message is 'Thông báo lỗi khi status = failed.';

create table meta.quality_run (
    check_result_id bigint generated always as identity primary key,
    run_id          uuid not null,
    batch_id        uuid references meta.ingestion_batch (batch_id),
    check_name      text not null,
    check_source    text not null check (check_source in ('rules', 'dbt')),
    severity        text not null check (severity in ('error', 'warning')),
    passed          boolean not null,
    observed_value  numeric,
    threshold       text,
    message         text,
    ran_at          timestamptz not null default now()
);
create index on meta.quality_run (run_id);
create index on meta.quality_run (ran_at desc);
comment on table  meta.quality_run                 is 'Kết quả từng check trong mỗi lần chạy make quality. Dashboard đọc thẳng bảng này.';
comment on column meta.quality_run.check_result_id is 'Khóa kỹ thuật của một kết quả check.';
comment on column meta.quality_run.run_id          is 'Một lần chạy quality.runner; mọi check cùng lần chạy chung run_id.';
comment on column meta.quality_run.batch_id        is 'Lô nạp thành công gần nhất tại thời điểm chạy check.';
comment on column meta.quality_run.check_name      is 'Tên check (rules.yml) hoặc tên test dbt (tiền tố dbt:).';
comment on column meta.quality_run.check_source    is 'rules = quality/rules.yml, dbt = test khai báo trong schema.yml.';
comment on column meta.quality_run.severity        is 'error chặn pipeline, warning chỉ báo.';
comment on column meta.quality_run.passed          is 'Check đạt hay không.';
comment on column meta.quality_run.observed_value  is 'Giá trị đo được (số dòng vi phạm, tỉ lệ, ...).';
comment on column meta.quality_run.threshold       is 'Ngưỡng so sánh, ví dụ "<= 0.05".';
comment on column meta.quality_run.message         is 'Lỗi SQL hoặc ghi chú thêm.';
comment on column meta.quality_run.ran_at          is 'Thời điểm chạy check.';
