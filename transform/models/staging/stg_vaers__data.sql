-- Làm sạch bảng VAERSDATA: chỉ lấy các batch nạp thành công, chuẩn hóa tên cột và ép kiểu dữ liệu.
-- Các giá trị ngoại lai (như tuổi âm hoặc ngày tháng bất hợp lý về mặt nghiệp vụ) sẽ được lọc ở tầng core.

with raw_data as (

    select r.*
    from {{ source('raw', 'vaers_data') }} as r
    inner join {{ source('meta', 'ingestion_batch') }} as b
        on r._batch_id = b.batch_id
    where b.status = 'success'

)

select
    nullif(trim("VAERS_ID"), '') as vaers_id,
    case
        when trim("RECVDATE") ~ '^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/\d{4}$'
            then to_date(trim("RECVDATE"), 'MM/DD/YYYY')
    end as recvdate,
    upper(nullif(trim("STATE"), '')) as state,
    nullif(trim("AGE_YRS"), '')::numeric as age_yrs,
    nullif(trim("CAGE_YR"), '')::numeric as cage_yr,
    nullif(trim("CAGE_MO"), '')::numeric as cage_mo,
    upper(nullif(trim("SEX"), '')) as sex,
    case
        when trim("RPT_DATE") ~ '^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/\d{4}$'
            then to_date(trim("RPT_DATE"), 'MM/DD/YYYY')
    end as rpt_date,
    nullif(trim("SYMPTOM_TEXT"), '') as symptom_text,
    upper(nullif(trim("DIED"), '')) as died,
    case
        when trim("DATEDIED") ~ '^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/\d{4}$'
            then to_date(trim("DATEDIED"), 'MM/DD/YYYY')
    end as datedied,
    upper(nullif(trim("L_THREAT"), '')) as l_threat,
    upper(nullif(trim("ER_VISIT"), '')) as er_visit,
    upper(nullif(trim("HOSPITAL"), '')) as hospital,
    nullif(trim("HOSPDAYS"), '')::integer as hospdays,
    upper(nullif(trim("X_STAY"), '')) as x_stay,
    upper(nullif(trim("DISABLE"), '')) as disable,
    upper(nullif(trim("RECOVD"), '')) as recovd,
    case
        when trim("VAX_DATE") ~ '^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/\d{4}$'
            then to_date(trim("VAX_DATE"), 'MM/DD/YYYY')
    end as vax_date,
    case
        when trim("ONSET_DATE") ~ '^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/\d{4}$'
            then to_date(trim("ONSET_DATE"), 'MM/DD/YYYY')
    end as onset_date,
    nullif(trim("NUMDAYS"), '')::integer as numdays,
    nullif(trim("LAB_DATA"), '') as lab_data,
    upper(nullif(trim("V_ADMINBY"), '')) as v_adminby,
    upper(nullif(trim("V_FUNDBY"), '')) as v_fundby,
    nullif(trim("OTHER_MEDS"), '') as other_meds,
    nullif(trim("CUR_ILL"), '') as cur_ill,
    nullif(trim("HISTORY"), '') as history,
    nullif(trim("PRIOR_VAX"), '') as prior_vax,
    nullif(trim("SPLTTYPE"), '') as splttype,
    nullif(trim("FORM_VERS"), '') as form_vers,
    case
        when trim("TODAYS_DATE") ~ '^(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/\d{4}$'
            then to_date(trim("TODAYS_DATE"), 'MM/DD/YYYY')
    end as todays_date,
    upper(nullif(trim("BIRTH_DEFECT"), '')) as birth_defect,
    upper(nullif(trim("OFC_VISIT"), '')) as ofc_visit,
    upper(nullif(trim("ER_ED_VISIT"), '')) as er_ed_visit,
    nullif(trim("ALLERGIES"), '') as allergies,
    nullif(trim("ORDER"), '')::integer as vax_order,
    _batch_id as batch_id,
    _ingested_at as ingested_at,
    _row_hash as row_hash
from raw_data