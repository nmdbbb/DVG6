-- dim_vaccine. Grain: một dòng cho mỗi sản phẩm vắc xin (vax_type, vax_manu chuẩn hóa, vax_name), cộng dòng unknown (-1).
-- Gom tên nhà sản xuất về 3 giá trị chuẩn PFIZER-BIONTECH, MODERNA, JANSSEN; còn lại vào OTHER (Issue #13).

with normalized as (

    select
        coalesce(vax_type, 'UNKNOWN') as vax_type,
        case
            when vax_manu like '%PFIZER%' or vax_manu like '%BIONTECH%' then 'PFIZER-BIONTECH'
            when vax_manu like '%MODERNA%' then 'MODERNA'
            when vax_manu like '%JANSSEN%' or vax_manu like '%JOHNSON%' then 'JANSSEN'
            else 'OTHER'
        end                           as vax_manu,
        coalesce(vax_name, 'UNKNOWN') as vax_name
    from {{ ref('stg_vaers__vax') }}

),

distinct_vax as (

    select distinct
        vax_type,
        vax_manu,
        vax_name
    from normalized
    where not (vax_type = 'UNKNOWN' and vax_manu = 'UNKNOWN' and vax_name = 'UNKNOWN')

)

select
    (row_number() over (order by vax_type, vax_manu, vax_name))::bigint as vaccine_key,
    vax_type || '|' || vax_manu || '|' || vax_name                      as vaccine_id,
    vax_type,
    vax_manu,
    vax_name
from distinct_vax

union all

select
    -1::bigint as vaccine_key,
    'UNKNOWN'  as vaccine_id,
    'UNKNOWN'  as vax_type,
    'UNKNOWN'  as vax_manu,
    'UNKNOWN'  as vax_name