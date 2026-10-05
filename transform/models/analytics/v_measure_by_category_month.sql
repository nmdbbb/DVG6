-- Câu hỏi: độ đo biến động theo tháng ra sao ở từng nhóm thực thể? (phục vụ trang Explore, M6)

select
    date_trunc('month', f.event_date)::date as month,
    coalesce(d.category, 'UNKNOWN')         as category,
    count(*)                                as n_records,
    count(f.measure_value)                  as n_measured,
    sum(f.measure_value)                    as total_measure,
    avg(f.measure_value)                    as avg_measure
from {{ ref('fct_main') }} as f
join {{ ref('dim_entity') }} as d
    on d.entity_key = f.entity_key
group by 1, 2
