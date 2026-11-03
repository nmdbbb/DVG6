-- fct_report_symptom. Grain: một dòng cho mỗi cặp (report_key, symptom_key) của báo cáo trong fct_report.
-- Triệu chứng lặp lại trong cùng một báo cáo được khử trùng lặp để chỉ đếm một lần (data_contract.md §1).

with report_symptoms as (

    select
        r.report_key,
        regexp_replace(
            regexp_replace(
                regexp_replace(trim(s.symptom_name), '\s+', ' ', 'g'),
                '(?i)^vaccination site\y',
                'Injection site'
            ),
            '(?i)\yvaccination site\y',
            'injection site',
            'g'
        ) as clean_symptom_name
    from {{ ref('fct_report') }} as r
    join {{ ref('stg_vaers__symptoms') }} as s
        on s.vaers_id = r.vaers_id
    where s.symptom_name is not null
      and trim(s.symptom_name) <> ''

)

select distinct
    rs.report_key,
    coalesce(d.symptom_key, -1)::bigint as symptom_key
from report_symptoms as rs
left join {{ ref('dim_symptom') }} as d
    on d.symptom_name = rs.clean_symptom_name
   and d.symptom_key <> -1