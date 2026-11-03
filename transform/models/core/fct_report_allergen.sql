-- fct_report_allergen. Grain: một dòng cho mỗi cặp (report_key, allergen_key) của báo cáo trong fct_report.
-- Các mục không phải dị ứng (NONE, NKDA, N/A...) không sinh dòng; mục không khớp từ điển trỏ vào UNMAPPED (data_contract.md §4).

with {{ allergen_token_mapping_cte() }},

report_allergy_text as (

    select
        r.report_key,
        d.allergies
    from {{ ref('fct_report') }} as r
    join (
        select distinct on (vaers_id)
            vaers_id,
            allergies
        from {{ ref('stg_vaers__data') }}
        where allergies is not null
        order by vaers_id, ingested_at desc, row_hash
    ) as d
        on d.vaers_id = r.vaers_id

),

report_tokens as (

    select
        rat.report_key,
        {{ clean_allergy_token('raw_item') }} as cleaned_token
    from report_allergy_text as rat
    cross join lateral regexp_split_to_table(rat.allergies, '[,;\n\r/]+') as raw_item

),

mapped_allergens as (

    select
        rt.report_key,
        coalesce(da.allergen_key, -1)::bigint as allergen_key,
        tm.match_type,
        case tm.match_type
            when 'exact' then 1
            when 'fuzzy' then 2
            else 3
        end as match_priority
    from report_tokens as rt
    join token_mapping as tm
        on tm.cleaned_token = rt.cleaned_token
    left join {{ ref('dim_allergen') }} as da
        on da.canonical_name = tm.canonical_name
       and da.allergen_key <> -1
    where rt.cleaned_token <> ''
      and tm.match_type in ('exact', 'fuzzy', 'unmapped')

)

select distinct on (report_key, allergen_key)
    report_key,
    allergen_key,
    match_type
from mapped_allergens
order by report_key, allergen_key, match_priority asc