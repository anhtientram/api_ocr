# AI Analysis Rules

## Allowed
- Trích xuất chỉ số lab/ultrasound thành JSON có `key`, `value`, `unit`, `confidence`, `bbox`
- Tóm tắt hành chính/lâm sàng **đã anonymize** trong ≤ ~30 giây đọc
- Gắn `needs_human_verify` khi confidence thấp hoặc đơn vị mơ hồ

## Forbidden (hard)
- Chẩn đoán bệnh
- Gợi ý / kê thuốc / liều dùng
- Suy luận nguyên nhân vô sinh / tiên lượng
- “Bác sĩ nên…” / “khuyến nghị điều trị…”

## Prompt hygiene
- System prompt versioned (file trong repo, không hard-code rải rác)
- Structured output / JSON schema bắt buộc
- Post-filter regex/heuristic strip câu chẩn đoán/kê đơn (best-effort + test)

## Models
- Chọn model qua env; ghi `usage.model` mọi response
- Không gửi ảnh có watermark tên bệnh nhân nếu client quên strip — reject nếu detect PII pattern mạnh (SĐT VN) trong OCR text trước khi gọi AI (log chỉ `pii_detected=true`)
