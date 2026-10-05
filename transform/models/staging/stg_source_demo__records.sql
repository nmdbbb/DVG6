-- Staging: đổi tên, ép kiểu, cắt khoảng trắng, chuẩn hóa hoa/thường, lọc lô fail.
-- Không bỏ dòng, không khử trùng lặp nghiệp vụ, không join dimension — các việc đó ở core.

with raw as (

    select r.*
    from {{ source('raw', 'source_demo_records') }} as r
    join {{ source('meta', 'ingestion_batch') }} as b
        on b.batch_id = r._batch_id
    where b.status = 'success'

)

select
    nullif(trim(record_id), '')                          as record_id,
    upper(nullif(trim(entity_code), ''))                 as entity_id,
    nullif(trim(entity_name), '')                        as entity_name,
    upper(nullif(trim(category), ''))                    as category,
    nullif(trim(event_date), '')::date                   as event_date,
    nullif(trim(measure_value), '')::numeric(14, 4)      as measure_value,
    _batch_id                                            as batch_id,
    _ingested_at                                         as ingested_at,
    _row_hash                                            as row_hash
from raw
