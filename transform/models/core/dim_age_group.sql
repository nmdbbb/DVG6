-- dim_age_group. Grain: 7 nhóm tuổi cố định theo bài báo cộng dòng UNKNOWN (-1) (decision_log #30).

select
    age_group_key::bigint,
    age_group_label,
    min_age::numeric,
    max_age::numeric,
    sort_order::integer
from (
    values
        (1,  '5-11',    5,    11,   1),
        (2,  '12-15',   12,   15,   2),
        (3,  '16-18',   16,   18,   3),
        (4,  '19-30',   19,   30,   4),
        (5,  '31-50',   31,   50,   5),
        (6,  '51-65',   51,   65,   6),
        (7,  '66+',     66,   120,  7),
        (-1, 'UNKNOWN', null, null, 99)
) as t(age_group_key, age_group_label, min_age, max_age, sort_order)