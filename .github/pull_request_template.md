## Việc làm trong PR này

<!-- Một PR một việc. Không trộn thêm connector với sửa schema. -->

## Checklist merge (docs/data_contract.md §6)

- [ ] CI xanh (lint + pipeline)
- [ ] Chạm `db/` hoặc `transform/models/core/` → Data Architect đã duyệt
- [ ] Chạm `analysis/`, `quality/` hoặc kết luận thống kê → Analysis & Quality Owner đã duyệt
- [ ] Có phép làm sạch dữ liệu → đã thêm dòng vào `docs/cleaning_log.md`
- [ ] Có quyết định đánh đổi → đã thêm dòng vào `docs/decision_log.md`
- [ ] Thêm migration → file MỚI, không sửa file đã merge
- [ ] Không có file trong `data/`, không có `.env`
