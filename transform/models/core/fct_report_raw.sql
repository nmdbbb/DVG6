-- fct_report_raw. Grain: một dòng cho mỗi báo cáo hợp lệ năm 2021 (COVID19, có triệu chứng) trước khi khử trùng lặp.
-- Làm sạch ngày và tuổi vô lý theo data_contract.md 3, 4 và decision_log.md 28, 30, 32.

with dedup_raw_id as (

    select distinct on (vaers_id) *
    from {{ ref('stg_vaers__data') }}
    where vaers_id is not null
      and vaers_id ~ '^\d+$'
      and recvdate >= date '2021-01-01'
      and recvdate <= date '2021-12-31'
    order by vaers_id, ingested_at desc, row_hash

),

covid_reports as (

    select distinct vaers_id
    from {{ ref('stg_vaers__vax') }}
    where vax_type = 'COVID19'

),

symptom_counts as (

    select
        s.vaers_id,
        count(distinct regexp_replace(
            regexp_replace(
                regexp_replace(trim(s.symptom_name), '\s+', ' ', 'g'),
                '(?i)^vaccination site\y',
                'Injection site'
            ),
            '(?i)\yvaccination site\y',
            'injection site',
            'g'
        ))::integer as n_symptoms
    from {{ ref('stg_vaers__symptoms') }} as s
    where s.symptom_name is not null
      and trim(s.symptom_name) <> ''
    group by s.vaers_id

),

cleaned as (

    select
        d.vaers_id::bigint as report_key,
        d.vaers_id,
        d.recvdate,
        case
            when d.vax_date >= date '2020-12-01'
             and d.vax_date <= d.recvdate
                then d.vax_date
        end as clean_vax_date,
        case
            when d.vax_date >= date '2020-12-01'
             and d.vax_date <= d.recvdate
             and d.onset_date is not null
             and d.onset_date >= d.vax_date
                then d.onset_date
        end as clean_onset_date,
        case
            when d.age_yrs >= 0 and d.age_yrs <= 120
                then d.age_yrs
        end as clean_age_yrs,
        case
            when d.hospdays >= 0 and d.hospdays <= 365
                then d.hospdays
        end as clean_hospdays,
        d.sex,
        d.state,
        sc.n_symptoms,
        coalesce(d.died = 'Y', false)      as died,
        coalesce(d.hospital = 'Y', false)  as hospital,
        coalesce(d.er_visit = 'Y' or d.er_ed_visit = 'Y', false) as er_visit,
        coalesce(d.l_threat = 'Y', false)  as life_threatening,
        coalesce(d.disable = 'Y', false)   as disabled,
        d.batch_id
    from dedup_raw_id as d
    join covid_reports as c
        on c.vaers_id = d.vaers_id
    join symptom_counts as sc
        on sc.vaers_id = d.vaers_id

)

select
    c.report_key,
    c.vaers_id,
    coalesce(dt_recv.date_key, -1)::bigint     as received_date_key,
    coalesce(dt_vax.date_key, -1)::bigint      as vax_date_key,
    coalesce(ag.age_group_key, -1)::bigint     as age_group_key,
    coalesce(sx.sex_key, -1)::bigint           as sex_key,
    coalesce(st.state_key, -1)::bigint         as state_key,
    c.recvdate,
    c.clean_vax_date                           as vax_date,
    c.clean_onset_date                         as onset_date,
    c.clean_age_yrs                            as age_yrs,
    (c.clean_onset_date - c.clean_vax_date)::integer as numdays,
    c.clean_hospdays                           as hospdays,
    c.n_symptoms,
    c.died,
    c.hospital,
    c.er_visit,
    c.life_threatening,
    c.disabled,
    c.batch_id
from cleaned as c
left join {{ ref('dim_date') }} as dt_recv
    on dt_recv.date_day = c.recvdate
   and dt_recv.date_key <> -1
left join {{ ref('dim_date') }} as dt_vax
    on dt_vax.date_day = c.clean_vax_date
   and dt_vax.date_key <> -1
left join {{ ref('dim_age_group') }} as ag
    on c.clean_age_yrs is not null
   and floor(c.clean_age_yrs) between ag.min_age and ag.max_age
   and ag.age_group_key <> -1
left join {{ ref('dim_sex') }} as sx
    on sx.sex_code = c.sex
   and sx.sex_key <> -1
left join {{ ref('dim_state') }} as st
    on st.state_code = c.state
   and st.state_key <> -1