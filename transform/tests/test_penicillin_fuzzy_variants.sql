-- Đảm bảo các biến thể viết sai chính tả phổ biến của Penicillin và Sulfa
-- được gom đúng về một khóa chuẩn duy nhất (allergen_key > 0).

with {{ allergen_token_mapping_cte() }},

penicillin_check as (

    select
        count(distinct d.allergen_key) as key_cnt,
        count(*)                       as matched_variants
    from token_mapping as m
    join {{ ref('dim_allergen') }} as d
        on d.canonical_name = m.canonical_name
    where m.cleaned_token in ('PENICILLIN', 'PENECELLIN', 'PENECILLIN', 'PENECILIN')
      and d.allergen_key > 0
      and d.canonical_name = 'PENICILLIN'

),

sulfa_check as (

    select
        count(distinct d.allergen_key) as key_cnt,
        count(*)                       as matched_variants
    from token_mapping as m
    join {{ ref('dim_allergen') }} as d
        on d.canonical_name = m.canonical_name
    where m.cleaned_token in ('SULFA', 'SULPHA', 'SULFIDES', 'SULFITE', 'SULFATE')
      and d.allergen_key > 0
      and d.canonical_name = 'SULFA'

)

select 'penicillin_variants_not_grouped' as failure_reason
from penicillin_check
where key_cnt <> 1 or matched_variants <> 4

union all

select 'sulfa_variants_not_grouped' as failure_reason
from sulfa_check
where key_cnt <> 1 or matched_variants <> 5