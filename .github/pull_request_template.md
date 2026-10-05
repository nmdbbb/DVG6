## Việc làm trong PR này

Closes #

<!-- Một PR một việc. Nhánh đặt tên <vai>/<việc>, ví dụ ingest/source-a. -->

## Checklist merge (README → Nhận nhiệm vụ → c)

- [ ] CI xanh (`lint` + `pipeline`) — bắt buộc với mọi PR
- [ ] Chạm `db/` hoặc `transform/models/core/` → Data Architect duyệt; có đánh đổi thì thêm dòng `docs/decision_log.md`
- [ ] Có code làm sạch dữ liệu → Data Architect duyệt; thêm dòng `docs/cleaning_log.md` kèm số dòng trước/sau
- [ ] Chạm `analysis/` hoặc kết luận thống kê → Analysis Lead duyệt; ghi giả định mô hình đã kiểm
- [ ] Sửa ngoài thư mục mình sở hữu → đã hỏi người sở hữu (tag họ làm reviewer)
- [ ] Migration mới là file mới, không sửa file đã merge
- [ ] Không có file trong `data/`, không có `.env`
