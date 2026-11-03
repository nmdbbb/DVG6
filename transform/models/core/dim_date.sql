-- dim_date. Grain: một dòng cho mỗi ngày dương lịch từ 2020-01-01 đến 2025-12-31, cộng dòng UNKNOWN (-1) (decision_log #30).

with spine as (

    select d::date as date_day
    from generate_series(
        date '2020-01-01',
        date '2025-12-31',
        interval '1 day'
    ) as d

)

select
    to_char(date_day, 'YYYYMMDD')::bigint as date_key,
    date_day,
    to_char(date_day, 'YYYY-MM-DD')       as date_label,
    extract(year from date_day)::integer  as year,
    extract(month from date_day)::integer as month,
    extract(day from date_day)::integer   as day_of_month
from spine

union all

select
    -1::bigint       as date_key,
    date '1900-01-01' as date_day,
    'UNKNOWN'        as date_label,
    null::integer    as year,
    null::integer    as month,
    null::integer    as day_of_month