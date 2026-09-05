# AI Intake Proxy (api_ocr) — Agent Guide

Microservice OCR + AI phân tích tài liệu y tế cho hệ thống **clinic-booking** (NTT Mini CRM / Remote Prescription).

## Product goal

Nhận ảnh/PDF phiếu xét nghiệm (đã anonymize từ Web App) → OCR → AI bóc chỉ số JSON + bbox source-trace + (tuỳ chọn) summary 30s → trả về cho `AiProxyClient` của clinic-booking.

## Stack (chốt)

- Python 3.11+ / FastAPI
- Tesseract OCR (`vie` + `eng`) + pdf2image/Poppler
- AI provider qua env (OpenAI / Gemini / Claude) — structured JSON output
- Docker 1 service; auth bằng internal secret key
- Không lưu PII; file tạm xoá sau xử lý

## Consumer

| Hệ thống | Path tham chiếu trong monorepo |
|---|---|
| Web App | `clinic-booking/` |
| Tasks Phase 2 | `clinic-booking/tasks.json` → P2.01–P2.09 |
| OCR workflow Web App | `clinic-booking/.agents/workflows/dev2/dev2-p2.03-ocr-reader.md` |
| Form Tầng 3 | `clinic-booking/docs/architecture/form-3-tier.md` |

## Priorities

1. Zero PII trong log / payload gửi model (SĐT, họ tên, địa chỉ đã bị Web App strip trước khi gọi).
2. AI **không** chẩn đoán, **không** kê thuốc.
3. Confidence thấp → đánh dấu cần Human Verify; không bịa chỉ số.
4. Proxy down / OCR fail → trả lỗi có cấu trúc; Web App fallback thủ công (P2.08).
5. Contract API ổn định với `AiProxyClient` — không đổi field breaking mà không version.

## Ownership boundary

| Repo này (`api_ocr`) | Repo `clinic-booking` |
|---|---|
| OCR, AI extract, summary, bbox, token cost | PII anonymizer, AiProxyClient, UI Source Trace, Risk Flags, fallback |
| Endpoint `/v1/ocr/*`, `/v1/analyze/*` | Lưu `ai_extraction_logs`, B2 verify |

## Do not do

- Không tự chẩn đoán / gợi ý thuốc trong response.
- Không log raw text chứa PII nếu vẫn lọt từ client.
- Không trả public URL file.
- Không hard-code API key trong repo.
- Không phụ thuộc Laravel/Filament — đây là service độc lập.
