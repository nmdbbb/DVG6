-- dim_allergen. Grain: một dòng cho mỗi chất gây dị ứng đã chuẩn hóa (canonical_name), kèm UNMAPPED và UNKNOWN (-1).

with {{ allergen_token_mapping_cte() }},

aggregated as (

    select
        canonical_name,
        coalesce(sum(mention_count) filter (where match_type = 'exact'), 0)::bigint    as exact_mention_count,
        coalesce(sum(mention_count) filter (where match_type = 'fuzzy'), 0)::bigint    as fuzzy_mention_count,
        coalesce(sum(mention_count) filter (where match_type = 'unmapped'), 0)::bigint as unmapped_mention_count,
        coalesce(sum(mention_count), 0)::bigint                                        as total_mention_count
    from token_mapping
    where match_type in ('exact', 'fuzzy', 'unmapped')
    group by canonical_name

)

select
    (row_number() over (
        order by
            case when canonical_name = 'UNMAPPED' then 1 else 0 end,
            canonical_name
    ))::bigint             as allergen_key,
    canonical_name,
    canonical_name         as allergen_label,
    exact_mention_count,
    fuzzy_mention_count,
    unmapped_mention_count,
    total_mention_count
from aggregated

union all

select
    -1::bigint             as allergen_key,
    'UNKNOWN'              as canonical_name,
    'UNKNOWN'              as allergen_label,
    0::bigint              as exact_mention_count,
    0::bigint              as fuzzy_mention_count,
    0::bigint              as unmapped_mention_count,
    0::bigint              as total_mention_count