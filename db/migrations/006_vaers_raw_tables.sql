-- 006: ba bảng raw VAERS, theo header của ZIP 2021 đã kiểm tra.
-- Giữ nguyên tên cột nguồn (kể cả ORDER), dùng identifier có dấu ngoặc kép.
-- Mọi giá trị nguồn là text, không ép kiểu/làm sạch/lọc COVID-19 tại raw.
-- VAERS_ID không unique: một báo cáo có thể có nhiều dòng vắc xin/triệu chứng.

create table raw.vaers_data (
    "VAERS_ID" text,
    "RECVDATE" text,
    "STATE" text,
    "AGE_YRS" text,
    "CAGE_YR" text,
    "CAGE_MO" text,
    "SEX" text,
    "RPT_DATE" text,
    "SYMPTOM_TEXT" text,
    "DIED" text,
    "DATEDIED" text,
    "L_THREAT" text,
    "ER_VISIT" text,
    "HOSPITAL" text,
    "HOSPDAYS" text,
    "X_STAY" text,
    "DISABLE" text,
    "RECOVD" text,
    "VAX_DATE" text,
    "ONSET_DATE" text,
    "NUMDAYS" text,
    "LAB_DATA" text,
    "V_ADMINBY" text,
    "V_FUNDBY" text,
    "OTHER_MEDS" text,
    "CUR_ILL" text,
    "HISTORY" text,
    "PRIOR_VAX" text,
    "SPLTTYPE" text,
    "FORM_VERS" text,
    "TODAYS_DATE" text,
    "BIRTH_DEFECT" text,
    "OFC_VISIT" text,
    "ER_ED_VISIT" text,
    "ALLERGIES" text,
    "ORDER" text,
    _batch_id uuid not null references meta.ingestion_batch (batch_id),
    _source_name text not null,
    _ingested_at timestamptz not null default now(),
    _row_hash text not null,
    _payload jsonb
);

create unique index vaers_data_row_hash_uq on raw.vaers_data (_row_hash);
create index on raw.vaers_data (_batch_id);
create index on raw.vaers_data ("VAERS_ID");

comment on table raw.vaers_data is 'CSV VAERSDATA nguyên trạng. Một dòng cho mỗi bản ghi nguồn khác nhau theo _row_hash; chưa khử trùng lặp nghiệp vụ.';
comment on column raw.vaers_data."VAERS_ID" is 'Mã báo cáo VAERS, giữ dạng chuỗi gốc.';
comment on column raw.vaers_data."RECVDATE" is 'Ngày nhận báo cáo, chưa chuyển kiểu ngày.';
comment on column raw.vaers_data."STATE" is 'Bang như nguồn ghi.';
comment on column raw.vaers_data."AGE_YRS" is 'Tuổi tính bằng năm, giữ dạng chuỗi gốc.';
comment on column raw.vaers_data."CAGE_YR" is 'Trường CAGE_YR của nguồn, giữ nguyên để xử lý ở staging.';
comment on column raw.vaers_data."CAGE_MO" is 'Trường CAGE_MO của nguồn, giữ nguyên để xử lý ở staging.';
comment on column raw.vaers_data."SEX" is 'Mã giới tính gốc, chưa chuẩn hóa.';
comment on column raw.vaers_data."RPT_DATE" is 'Ngày báo cáo như nguồn ghi.';
comment on column raw.vaers_data."SYMPTOM_TEXT" is 'Mô tả triệu chứng bằng văn bản tự do nguyên gốc.';
comment on column raw.vaers_data."DIED" is 'Chỉ báo tử vong như nguồn ghi.';
comment on column raw.vaers_data."DATEDIED" is 'Ngày tử vong như nguồn ghi.';
comment on column raw.vaers_data."L_THREAT" is 'Chỉ báo đe dọa tính mạng như nguồn ghi.';
comment on column raw.vaers_data."ER_VISIT" is 'Chỉ báo đến phòng cấp cứu như nguồn ghi.';
comment on column raw.vaers_data."HOSPITAL" is 'Chỉ báo nhập viện như nguồn ghi.';
comment on column raw.vaers_data."HOSPDAYS" is 'Số ngày nằm viện, chưa ép kiểu số.';
comment on column raw.vaers_data."X_STAY" is 'Chỉ báo kéo dài nằm viện như nguồn ghi.';
comment on column raw.vaers_data."DISABLE" is 'Chỉ báo khuyết tật như nguồn ghi.';
comment on column raw.vaers_data."RECOVD" is 'Tình trạng hồi phục như nguồn ghi.';
comment on column raw.vaers_data."VAX_DATE" is 'Ngày tiêm, chưa chuyển kiểu ngày.';
comment on column raw.vaers_data."ONSET_DATE" is 'Ngày khởi phát triệu chứng, chưa chuyển kiểu ngày.';
comment on column raw.vaers_data."NUMDAYS" is 'Số ngày từ tiêm tới khởi phát, chưa ép kiểu số.';
comment on column raw.vaers_data."LAB_DATA" is 'Thông tin xét nghiệm nguyên gốc.';
comment on column raw.vaers_data."V_ADMINBY" is 'Thông tin đơn vị thực hiện tiêm như nguồn ghi.';
comment on column raw.vaers_data."V_FUNDBY" is 'Thông tin nguồn chi trả vắc xin như nguồn ghi.';
comment on column raw.vaers_data."OTHER_MEDS" is 'Thuốc khác đang dùng, văn bản nguyên gốc.';
comment on column raw.vaers_data."CUR_ILL" is 'Bệnh hiện tại, văn bản nguyên gốc.';
comment on column raw.vaers_data."HISTORY" is 'Tiền sử bệnh, văn bản nguyên gốc.';
comment on column raw.vaers_data."PRIOR_VAX" is 'Thông tin phản ứng với lần tiêm trước như nguồn ghi.';
comment on column raw.vaers_data."SPLTTYPE" is 'Trường SPLTTYPE của nguồn, chưa chuẩn hóa.';
comment on column raw.vaers_data."FORM_VERS" is 'Phiên bản biểu mẫu báo cáo như nguồn ghi.';
comment on column raw.vaers_data."TODAYS_DATE" is 'Ngày điền biểu mẫu như nguồn ghi.';
comment on column raw.vaers_data."BIRTH_DEFECT" is 'Chỉ báo dị tật bẩm sinh như nguồn ghi.';
comment on column raw.vaers_data."OFC_VISIT" is 'Chỉ báo khám tại phòng khám như nguồn ghi.';
comment on column raw.vaers_data."ER_ED_VISIT" is 'Chỉ báo khám cấp cứu như nguồn ghi.';
comment on column raw.vaers_data."ALLERGIES" is 'Tiền sử dị ứng nguyên gốc, giữ cả lỗi chính tả.';
comment on column raw.vaers_data."ORDER" is 'Trường ORDER của nguồn, giữ nguyên; không dùng làm khóa ở raw.';
comment on column raw.vaers_data._batch_id is 'Lô đầu tiên ghi dòng này, tham chiếu meta.ingestion_batch.';
comment on column raw.vaers_data._source_name is 'Tên connector nạp dữ liệu.';
comment on column raw.vaers_data._ingested_at is 'Thời điểm ghi vào raw.';
comment on column raw.vaers_data._row_hash is 'md5 của toàn bộ bản ghi gốc dạng JSON sắp khóa, tránh nạp lại cùng dòng.';
comment on column raw.vaers_data._payload is 'Bản ghi gốc đầy đủ dạng JSON, phục vụ kiểm tra parser.';

create table raw.vaers_symptoms (
    "VAERS_ID" text,
    "SYMPTOM1" text,
    "SYMPTOMVERSION1" text,
    "SYMPTOM2" text,
    "SYMPTOMVERSION2" text,
    "SYMPTOM3" text,
    "SYMPTOMVERSION3" text,
    "SYMPTOM4" text,
    "SYMPTOMVERSION4" text,
    "SYMPTOM5" text,
    "SYMPTOMVERSION5" text,
    "ORDER" text,
    _batch_id uuid not null references meta.ingestion_batch (batch_id),
    _source_name text not null,
    _ingested_at timestamptz not null default now(),
    _row_hash text not null,
    _payload jsonb
);

create unique index vaers_symptoms_row_hash_uq on raw.vaers_symptoms (_row_hash);
create index on raw.vaers_symptoms (_batch_id);
create index on raw.vaers_symptoms ("VAERS_ID");

comment on table raw.vaers_symptoms is 'CSV VAERSSYMPTOMS nguyên trạng. Một dòng cho mỗi bản ghi nguồn khác nhau theo _row_hash; giữ năm cặp cột triệu chứng, chưa unpivot.';
comment on column raw.vaers_symptoms."VAERS_ID" is 'Mã báo cáo VAERS; nhiều dòng có thể cùng mã.';
comment on column raw.vaers_symptoms."SYMPTOM1" is 'Triệu chứng thứ nhất như nguồn ghi.';
comment on column raw.vaers_symptoms."SYMPTOMVERSION1" is 'Phiên bản thuật ngữ của triệu chứng thứ nhất.';
comment on column raw.vaers_symptoms."SYMPTOM2" is 'Triệu chứng thứ hai như nguồn ghi.';
comment on column raw.vaers_symptoms."SYMPTOMVERSION2" is 'Phiên bản thuật ngữ của triệu chứng thứ hai.';
comment on column raw.vaers_symptoms."SYMPTOM3" is 'Triệu chứng thứ ba như nguồn ghi.';
comment on column raw.vaers_symptoms."SYMPTOMVERSION3" is 'Phiên bản thuật ngữ của triệu chứng thứ ba.';
comment on column raw.vaers_symptoms."SYMPTOM4" is 'Triệu chứng thứ tư như nguồn ghi.';
comment on column raw.vaers_symptoms."SYMPTOMVERSION4" is 'Phiên bản thuật ngữ của triệu chứng thứ tư.';
comment on column raw.vaers_symptoms."SYMPTOM5" is 'Triệu chứng thứ năm như nguồn ghi.';
comment on column raw.vaers_symptoms."SYMPTOMVERSION5" is 'Phiên bản thuật ngữ của triệu chứng thứ năm.';
comment on column raw.vaers_symptoms."ORDER" is 'Trường ORDER nguyên gốc, không dùng làm khóa ở raw.';
comment on column raw.vaers_symptoms._batch_id is 'Lô đầu tiên ghi dòng này, tham chiếu meta.ingestion_batch.';
comment on column raw.vaers_symptoms._source_name is 'Tên connector nạp dữ liệu.';
comment on column raw.vaers_symptoms._ingested_at is 'Thời điểm ghi vào raw.';
comment on column raw.vaers_symptoms._row_hash is 'md5 của toàn bộ bản ghi gốc dạng JSON sắp khóa, tránh nạp lại cùng dòng.';
comment on column raw.vaers_symptoms._payload is 'Bản ghi gốc đầy đủ dạng JSON, phục vụ kiểm tra parser.';

create table raw.vaers_vax (
    "VAERS_ID" text,
    "VAX_TYPE" text,
    "VAX_MANU" text,
    "VAX_LOT" text,
    "VAX_DOSE_SERIES" text,
    "VAX_ROUTE" text,
    "VAX_SITE" text,
    "VAX_NAME" text,
    "ORDER" text,
    _batch_id uuid not null references meta.ingestion_batch (batch_id),
    _source_name text not null,
    _ingested_at timestamptz not null default now(),
    _row_hash text not null,
    _payload jsonb
);

create unique index vaers_vax_row_hash_uq on raw.vaers_vax (_row_hash);
create index on raw.vaers_vax (_batch_id);
create index on raw.vaers_vax ("VAERS_ID");

comment on table raw.vaers_vax is 'CSV VAERSVAX nguyên trạng. Một dòng cho mỗi bản ghi nguồn khác nhau theo _row_hash; một báo cáo có thể chứa nhiều vắc xin, chưa lọc COVID19.';
comment on column raw.vaers_vax."VAERS_ID" is 'Mã báo cáo VAERS; nhiều dòng có thể cùng mã.';
comment on column raw.vaers_vax."VAX_TYPE" is 'Loại vắc xin nguyên gốc; chưa lọc COVID19.';
comment on column raw.vaers_vax."VAX_MANU" is 'Nhà sản xuất như nguồn ghi.';
comment on column raw.vaers_vax."VAX_LOT" is 'Số lô sản xuất như nguồn ghi.';
comment on column raw.vaers_vax."VAX_DOSE_SERIES" is 'Thông tin thứ tự liều như nguồn ghi.';
comment on column raw.vaers_vax."VAX_ROUTE" is 'Đường tiêm như nguồn ghi.';
comment on column raw.vaers_vax."VAX_SITE" is 'Vị trí tiêm như nguồn ghi.';
comment on column raw.vaers_vax."VAX_NAME" is 'Tên vắc xin như nguồn ghi.';
comment on column raw.vaers_vax."ORDER" is 'Trường ORDER nguyên gốc, không dùng làm khóa ở raw.';
comment on column raw.vaers_vax._batch_id is 'Lô đầu tiên ghi dòng này, tham chiếu meta.ingestion_batch.';
comment on column raw.vaers_vax._source_name is 'Tên connector nạp dữ liệu.';
comment on column raw.vaers_vax._ingested_at is 'Thời điểm ghi vào raw.';
comment on column raw.vaers_vax._row_hash is 'md5 của toàn bộ bản ghi gốc dạng JSON sắp khóa, tránh nạp lại cùng dòng.';
comment on column raw.vaers_vax._payload is 'Bản ghi gốc đầy đủ dạng JSON, phục vụ kiểm tra parser.';
