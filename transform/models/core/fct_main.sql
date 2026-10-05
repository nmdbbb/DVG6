-- fct_main. Grain: một dòng cho mỗi sự kiện đo (record_id).
-- Quyết định làm sạch (docs/cleaning_log.md):
--   #3 bỏ dòng thiếu record_id — không có khóa định danh thì không xác định được grain
--   #4 trùng record_id: giữ bản nạp sau cùng (ingested_at), hòa thì theo row_hash
--   #5 không map được thực thể: trỏ về entity_key = -1, không để rơi mất khi join

with stg as (

    select *
    from {{ ref('stg_source_demo__records') }}
    where record_id is not null

),

deduped as (

    select distinct on (record_id) *
    from stg
    order by record_id, ingested_at desc, row_hash

)

select
    s.record_id,
    coalesce(d.entity_key, -1) as entity_key,
    s.event_date,
    s.measure_value,
    s.batch_id
from deduped as s
left join {{ ref('dim_entity') }} as d
    on d.entity_id = s.entity_id
   and d.entity_key <> -1
