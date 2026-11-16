-- report_duplicate_map. Grain: một dòng cho mỗi báo cáo bị đánh dấu trùng, trỏ về kept_vaers_id (VAERS_ID nhỏ nhất).
-- Quy tắc tất định rule_version = 1 (analysis_plan.md 5, decision_log.md 31).

with eligible_reports as (

    select
        report_key,
        vaers_id,
        age_group_key,
        sex_key,
        state_key,
        vax_date_key
    from {{ ref('fct_report_raw') }}
    where age_group_key <> -1
      and sex_key <> -1
      and vax_date_key <> -1

),

normalized_covid_vax as (

    select
        v.vaers_id,
        case
            when v.vax_manu like '%PFIZER%' or v.vax_manu like '%BIONTECH%' then 'PFIZER-BIONTECH'
            when v.vax_manu like '%MODERNA%' then 'MODERNA'
            when v.vax_manu like '%JANSSEN%' or v.vax_manu like '%JOHNSON%' then 'JANSSEN'
            else 'OTHER'
        end as std_vax_manu
    from {{ ref('stg_vaers__vax') }} as v
    join eligible_reports as e
        on e.vaers_id = v.vaers_id
    where v.vax_type = 'COVID19'

),

vax_signatures as (

    select
        vaers_id,
        string_agg(distinct std_vax_manu, '|' order by std_vax_manu) as vax_manu_set
    from normalized_covid_vax
    group by vaers_id

),

symptom_signatures as (

    select
        s.vaers_id,
        string_agg(distinct d.symptom_key::text, ',' order by d.symptom_key::text) as symptom_key_set
    from {{ ref('stg_vaers__symptoms') }} as s
    join eligible_reports as e
        on e.vaers_id = s.vaers_id
    join {{ ref('dim_symptom') }} as d
        on d.symptom_name = regexp_replace(
            regexp_replace(
                regexp_replace(trim(s.symptom_name), '\s+', ' ', 'g'),
                '(?i)^vaccination site\y',
                'Injection site'
            ),
            '(?i)\yvaccination site\y',
            'injection site',
            'g'
        )
    where d.symptom_key <> -1
    group by s.vaers_id

),

ranked as (

    select
        e.vaers_id,
        first_value(e.vaers_id) over dup_window as kept_vaers_id,
        row_number() over dup_window            as rn
    from eligible_reports as e
    join vax_signatures as vs
        on vs.vaers_id = e.vaers_id
    join symptom_signatures as ss
        on ss.vaers_id = e.vaers_id
    window dup_window as (
        partition by
            e.age_group_key,
            e.sex_key,
            e.state_key,
            e.vax_date_key,
            vs.vax_manu_set,
            ss.symptom_key_set
        order by e.report_key asc
    )

)

select
    vaers_id,
    kept_vaers_id,
    1::integer as rule_version
from ranked
where rn > 1