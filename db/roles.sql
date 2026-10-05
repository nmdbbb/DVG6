-- Role và quyền theo từng schema. scripts/migrate.py chạy lại file này sau mỗi lần migrate
-- (idempotent), nên bảng mới tạo bởi migration luôn được cấp quyền đúng.
-- __XXX_PASSWORD__ được migrate.py thay bằng literal đã escape từ biến môi trường.

do $$
begin
    if not exists (select from pg_roles where rolname = 'etl_writer') then
        create role etl_writer login;
    end if;
    if not exists (select from pg_roles where rolname = 'api_reader') then
        create role api_reader login;
    end if;
    if not exists (select from pg_roles where rolname = 'analyst') then
        create role analyst login;
    end if;
end
$$;

alter role etl_writer with login password __ETL_WRITER_PASSWORD__;
alter role api_reader with login password __API_READER_PASSWORD__;
alter role analyst    with login password __ANALYST_PASSWORD__;

comment on role etl_writer is 'Ingestion, transform (dbt), quality. Ghi raw/staging/core/analytics/meta.';
comment on role api_reader is 'FastAPI. Chỉ SELECT trên analytics và meta, không chạm raw.';
comment on role analyst    is 'Notebook phân tích. Chỉ SELECT trên core và analytics.';

-- ---------------------------------------------------------------- etl_writer
grant usage, create on schema raw, staging, core, analytics, meta to etl_writer;
-- raw chỉ ghi thêm: không cấp UPDATE/DELETE, nên nguyên tắc "raw bất biến" được database ép buộc.
grant select, insert on all tables in schema raw to etl_writer;
grant select, insert, update on all tables in schema meta to etl_writer;
grant usage, select on all sequences in schema raw, meta to etl_writer;

-- ---------------------------------------------------------------- api_reader
grant usage on schema analytics, meta to api_reader;
grant select on all tables in schema analytics, meta to api_reader;
-- Bảng/view do dbt (chạy bằng etl_writer) tạo sau này cũng tự động đọc được.
alter default privileges for role etl_writer in schema analytics grant select on tables to api_reader;

-- ---------------------------------------------------------------- analyst
grant usage on schema core, analytics to analyst;
grant select on all tables in schema core, analytics to analyst;
alter default privileges for role etl_writer in schema core, analytics grant select on tables to analyst;
