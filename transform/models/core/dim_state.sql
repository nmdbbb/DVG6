-- dim_state. Grain: một dòng cho mỗi mã bang/lãnh thổ (2 chữ cái), cộng dòng UNKNOWN (-1).

with distinct_states as (

    select distinct state as state_code
    from {{ ref('stg_vaers__data') }}
    where state is not null
      and state ~ '^[A-Z]{2}$'
      and state <> 'UN'

)

select
    (row_number() over (order by state_code))::bigint as state_key,
    state_code
from distinct_states

union all

select
    -1::bigint as state_key,
    'UNKNOWN'  as state_code