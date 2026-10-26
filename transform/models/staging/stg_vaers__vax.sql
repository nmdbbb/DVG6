-- Chuẩn hóa dữ liệu vắc xin (VAERSVAX) từ các batch nạp thành công.

with raw_vax as (

    select r.*
    from {{ source('raw', 'vaers_vax') }} as r
    inner join {{ source('meta', 'ingestion_batch') }} as b
        on r._batch_id = b.batch_id
    where b.status = 'success'

)

select
    nullif(trim("VAERS_ID"), '') as vaers_id,
    upper(nullif(trim("VAX_TYPE"), '')) as vax_type,
    upper(nullif(trim("VAX_MANU"), '')) as vax_manu,
    nullif(trim("VAX_LOT"), '') as vax_lot,
    upper(nullif(trim("VAX_DOSE_SERIES"), '')) as vax_dose_series,
    upper(nullif(trim("VAX_ROUTE"), '')) as vax_route,
    upper(nullif(trim("VAX_SITE"), '')) as vax_site,
    nullif(trim("VAX_NAME"), '') as vax_name,
    nullif(trim("ORDER"), '')::integer as vax_order,
    _batch_id as batch_id,
    _ingested_at as ingested_at,
    _row_hash as row_hash
from raw_vax