-- dim_symptom. Grain: một dòng cho mỗi thuật ngữ MedDRA Preferred Term đã chuẩn hóa, cộng dòng unknown (-1).
-- Chuẩn hóa "vaccination site" -> "injection site" (Issue #13).

with cleaned as (

    select
        regexp_replace(
            regexp_replace(
                regexp_replace(trim(symptom_name), '\s+', ' ', 'g'),
                '(?i)^vaccination site\y',
                'Injection site'
            ),
            '(?i)\yvaccination site\y',
            'injection site',
            'g'
        ) as symptom_name
    from {{ ref('stg_vaers__symptoms') }}
    where symptom_name is not null

),

distinct_symptoms as (

    select distinct symptom_name
    from cleaned
    where symptom_name <> ''
      and upper(symptom_name) <> 'UNKNOWN'

)

select
    (row_number() over (order by upper(symptom_name), symptom_name))::bigint as symptom_key,
    symptom_name
from distinct_symptoms

union all

select
    -1::bigint as symptom_key,
    'UNKNOWN'  as symptom_name