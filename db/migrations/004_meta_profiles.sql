-- 004: profile bảng/cột do quality.runner ghi sau mỗi lần chạy.
-- API chỉ được đọc analytics + meta, nên số dòng và tỉ lệ NULL của raw/staging/core
-- phải được etl_writer đo sẵn và ghi vào đây cho trang Overview và Catalog.

create table meta.table_profile (
    run_id       uuid        not null,
    schema_name  text        not null,
    table_name   text        not null,
    row_count    bigint      not null,
    profiled_at  timestamptz not null default now(),
    primary key (run_id, schema_name, table_name)
);
comment on table  meta.table_profile             is 'Số dòng từng bảng ở mọi tầng, đo sau mỗi lần chạy quality.';
comment on column meta.table_profile.run_id      is 'Lần chạy quality.runner (khớp meta.quality_run.run_id).';
comment on column meta.table_profile.schema_name is 'Tầng: raw, staging, core, analytics.';
comment on column meta.table_profile.table_name  is 'Tên bảng hoặc view.';
comment on column meta.table_profile.row_count   is 'Số dòng tại thời điểm đo.';
comment on column meta.table_profile.profiled_at is 'Thời điểm đo.';

create table meta.column_profile (
    run_id       uuid        not null,
    schema_name  text        not null,
    table_name   text        not null,
    column_name  text        not null,
    null_count   bigint      not null,
    null_rate    numeric     not null,
    profiled_at  timestamptz not null default now(),
    primary key (run_id, schema_name, table_name, column_name)
);
comment on table  meta.column_profile             is 'Số và tỉ lệ NULL từng cột ở mọi tầng, đo sau mỗi lần chạy quality.';
comment on column meta.column_profile.run_id      is 'Lần chạy quality.runner.';
comment on column meta.column_profile.schema_name is 'Tầng.';
comment on column meta.column_profile.table_name  is 'Tên bảng hoặc view.';
comment on column meta.column_profile.column_name is 'Tên cột.';
comment on column meta.column_profile.null_count  is 'Số dòng NULL.';
comment on column meta.column_profile.null_rate   is 'null_count / row_count (0 nếu bảng rỗng).';
comment on column meta.column_profile.profiled_at is 'Thời điểm đo.';
