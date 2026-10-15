Patch cho vai trò Crawler B & Mock server

Các file trong patch giữ nguyên đường dẫn tương đối của repo DVG6:
- ingestion/sources/openfda.py: connector openFDA
- ingestion/registry.py: đăng ký nguồn openfda, vẫn giữ source_demo để không phá test M1-M4
- ingestion/tests/test_openfda.py: test parse/hash/render/pagination
- mock_server/seed.py: không đưa trường kỹ thuật _source_payload vào cột HTML

Lưu ý migration:
 docs/sources.md đang ghi migration 006 dùng chung cho raw.vaers_data, raw.vaers_symptoms,
 raw.vaers_vax và raw.openfda_substances. Migration 006 nên do người sở hữu VAERS/Crawler A
 tạo một lần, có đủ bốn bảng; không thêm một migration 006 độc lập ở nhánh này để tránh trùng số.

API openFDA giới hạn skip <= 25000. Connector chỉ lấy tối đa các trang có skip 0..25000,
không tuyên bố snapshot là toàn bộ 262k nhãn. Chạy thử --limit 10 trước.
