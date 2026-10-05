-- 001: các tầng dữ liệu. Dữ liệu chảy một chiều raw -> staging -> core -> analytics; meta ghi nhật ký vận hành.
-- (meta được scripts/migrate.py tạo trước để giữ bảng schema_version, ở đây chỉ gắn comment.)

create schema if not exists raw;
create schema if not exists staging;
create schema if not exists core;
create schema if not exists analytics;
create schema if not exists meta;

comment on schema raw       is 'Bản sao nguyên trạng của nguồn. Chỉ ghi thêm, mọi cột nghiệp vụ là text. Chỉ ingestion được ghi.';
comment on schema staging   is 'Đã đổi tên cột, ép kiểu, cắt khoảng trắng, lọc lô fail. Một model cho mỗi bảng raw. Chỉ transform được ghi.';
comment on schema core      is 'Star schema dim_*/fct_*: làm sạch thật, có khóa thay thế. Chỉ transform được ghi.';
comment on schema analytics is 'View tổng hợp sẵn phục vụ dashboard. API chỉ đọc schema này và meta.';
comment on schema meta      is 'Nhật ký vận hành: nguồn, lô nạp, kết quả quality, profile bảng, phiên bản schema.';
