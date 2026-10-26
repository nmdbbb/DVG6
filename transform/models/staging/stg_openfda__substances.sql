-- Trích xuất và làm phẳng (flatten) danh sách hoạt chất từ chuỗi JSON của openFDA.
-- Mỗi dòng đầu ra tương ứng với một tên hoạt chất duy nhất (lấy theo bản ghi mới nhất).

with raw_substances as (

    select r.*
    from {{ source('raw', 'openfda_substances') }} as r
    inner join {{ source('meta', 'ingestion_batch') }} as b
        on r._batch_id = b.batch_id
    where b.status = 'success'
      and nullif(trim(r.substance_name), '') is not null

),

expanded as (

    select
        nullif(trim(r.spl_id), '') as spl_id,
        upper(nullif(trim(elem.val), '')) as substance_name,
        r._batch_id as batch_id,
        r._ingested_at as ingested_at,
        r._row_hash as raw_row_hash
    from raw_substances as r
    cross join lateral jsonb_array_elements_text(
        case
            when left(trim(r.substance_name), 1) = '['
                then r.substance_name::jsonb
            else jsonb_build_array(r.substance_name)
        end
    ) as elem(val)
    where nullif(trim(elem.val), '') is not null

)

select distinct on (substance_name)
    substance_name,
    spl_id,
    batch_id,
    ingested_at,
    raw_row_hash as row_hash
from expanded
order by substance_name, ingested_at desc, raw_row_hash