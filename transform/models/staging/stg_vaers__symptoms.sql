-- Chuyển đổi (unpivot) 5 nhóm cột SYMPTOM1..SYMPTOM5 về dạng dòng đơn.
-- Loại bỏ các vị trí triệu chứng trống; việc khử trùng lặp triệu chứng trên cùng một ca sẽ thực hiện ở tầng core.

with raw_symptoms as (

    select r.*
    from {{ source('raw', 'vaers_symptoms') }} as r
    inner join {{ source('meta', 'ingestion_batch') }} as b
        on r._batch_id = b.batch_id
    where b.status = 'success'

),

unpivoted as (

    select
        nullif(trim(r."VAERS_ID"), '') as vaers_id,
        u.symptom_slot,
        nullif(trim(u.symptom_name), '') as symptom_name,
        nullif(trim(u.symptom_version), '')::numeric as symptom_version,
        nullif(trim(r."ORDER"), '')::integer as symptom_order,
        r._batch_id as batch_id,
        r._ingested_at as ingested_at,
        r._row_hash as raw_row_hash,
        md5(r._row_hash || ':' || u.symptom_slot::text) as symptom_row_id
    from raw_symptoms as r
    cross join lateral (
        values
            (1, r."SYMPTOM1", r."SYMPTOMVERSION1"),
            (2, r."SYMPTOM2", r."SYMPTOMVERSION2"),
            (3, r."SYMPTOM3", r."SYMPTOMVERSION3"),
            (4, r."SYMPTOM4", r."SYMPTOMVERSION4"),
            (5, r."SYMPTOM5", r."SYMPTOMVERSION5")
    ) as u(symptom_slot, symptom_name, symptom_version)
    where nullif(trim(u.symptom_name), '') is not null

)

select *
from unpivoted