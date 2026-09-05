# PII & Security

## PII
- Client **phải** anonymize trước (clinic-booking P2.02). Proxy coi payload là đã sạch.
- Vẫn scan OCR text: pattern SĐT VN (`0\\d{9,10}`), họ tên nếu có field riêng → redacted trước khi gửi AI; response `warnings` có `pii_redacted`.
- Cấm log: raw file path user, SĐT, họ tên, địa chỉ, full raw OCR nếu đã phát hiện PII.

## Auth
- Mọi `/v1/*` cần `X-AI-Proxy-Key`
- Rate limit theo key
- Không commit `.env` / secret

## Retention
- File upload chỉ trên disk/tmp ephemeral; xoá ngay sau request (hoặc TTL ≤ vài phút)
- Không persist ảnh bệnh nhân mặc định; chỉ có thể persist metrics usage (không PII)

## Medical data
- Chỉ số lab vẫn là dữ liệu nhạy cảm — mã hoá at-rest nếu lưu cache; ưu tiên không lưu
