-- fct_report. Grain: một dòng cho mỗi báo cáo đã khử trùng lặp (vaers_id duy nhất).
-- Tập con của fct_report_raw sau khi loại các báo cáo nằm trong report_duplicate_map.

select r.*
from {{ ref('fct_report_raw') }} as r
where not exists (
    select 1
    from {{ ref('report_duplicate_map') }} as m
    where m.vaers_id = r.vaers_id
)