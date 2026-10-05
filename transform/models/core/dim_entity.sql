-- dim_entity. Grain: một dòng cho mỗi thực thể (entity_id), cộng một dòng unknown (key = -1).
-- Tên và nhóm lấy giá trị xuất hiện nhiều nhất của mỗi entity_id (cleaning_log #6).
-- entity_key là khóa thay thế ổn định theo thứ tự entity_id; dbt dựng lại toàn bảng mỗi lần chạy
-- cùng fct_main, nên khóa luôn khớp (decision_log #6).

with src as (

    select entity_id, entity_name, category
    from {{ ref('stg_source_demo__records') }}
    where entity_id is not null

),

resolved as (

    select
        entity_id,
        mode() within group (order by entity_name) as entity_name,
        mode() within group (order by category)    as category
    from src
    group by entity_id

)

select
    (row_number() over (order by entity_id))::bigint as entity_key,
    entity_id,
    entity_name,
    category
from resolved

union all

select -1::bigint, 'UNKNOWN', 'Unknown', null::text
