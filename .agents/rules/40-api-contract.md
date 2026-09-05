# API Contract Rules

Source of truth: `docs/API-CONTRACT.md`.

- Không đổi tên field breaking trong `/v1` (vd `extracted_parameters` → `params`).
- Thêm field mới: optional + documented.
- Error luôn `{ "error": { "code", "message", "request_id" } }`.
- `document_type` enum khớp clinic-booking: `lab|ultrasound|prescription|other`.
- `bbox` toạ độ pixel trên ảnh trang đã render (origin top-left); `page` 0-based.
- `usage` bắt buộc khi gọi AI (kể cả khi extract rỗng) để P2.09 đếm cost.
