-- fct_report_vaccine. Grain: một dòng cho mỗi bộ (report_key, vaccine_key, dose_series) của báo cáo trong fct_report.
-- Chỉ giữ dòng vắc xin thuộc báo cáo đã khử trùng lặp; không khớp dimension thì trỏ về -1 (data_contract.md §1, §4).

with report_vaccines as (

    select
        r.report_key,
        coalesce(v.vax_type, 'UNKNOWN') as vax_type,
        case
            when v.vax_manu like '%PFIZER%' or v.vax_manu like '%BIONTECH%' then 'PFIZER-BIONTECH'
            when v.vax_manu like '%MODERNA%' then 'MODERNA'
            when v.vax_manu like '%JANSSEN%' or v.vax_manu like '%JOHNSON%' then 'JANSSEN'
            else 'OTHER'
        end as vax_manu,
        coalesce(v.vax_name, 'UNKNOWN') as vax_name,
        case
            when v.vax_dose_series in ('UNK', 'UNKNOWN', '') then null
            else v.vax_dose_series
        end as dose_series
    from {{ ref('fct_report') }} as r
    join {{ ref('stg_vaers__vax') }} as v
        on v.vaers_id = r.vaers_id
    where v.vax_type = 'COVID19'

)

select distinct
    rv.report_key,
    coalesce(d.vaccine_key, -1)::bigint as vaccine_key,
    rv.dose_series
from report_vaccines as rv
left join {{ ref('dim_vaccine') }} as d
    on d.vax_type = rv.vax_type
   and d.vax_manu = rv.vax_manu
   and d.vax_name = rv.vax_name
   and d.vaccine_key <> -1