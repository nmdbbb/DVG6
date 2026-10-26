-- dim_sex. Grain: một dòng cho mỗi giới tính M / F / U (U là dòng unknown với sex_key = -1).

select
    sex_key::bigint,
    sex_code,
    sex_label
from (
    values
        (1,  'F', 'Female'),
        (2,  'M', 'Male'),
        (-1, 'U', 'UNKNOWN')
) as t(sex_key, sex_code, sex_label)