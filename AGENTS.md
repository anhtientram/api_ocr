# AI Intake Proxy (api_ocr) — Agent Guide

Microservice OCR + AI phân tích tài liệu y tế cho **clinic-booking** (Phase 2 Rev 0.2).

## Product goal

Nhận ảnh/PDF **derivative** (đã anonymize/orient từ Web App) → OCR → JSON chỉ số + `bbox_norm` (%) + (tuỳ chọn) summary → `AiProxyHmacClient`.

## Stack

- Python 3.11+ / FastAPI
- RapidOCR (default) / Tesseract fallback
- AI provider qua env (Gemini / OpenAI-compatible)
- Auth: HMAC Rev 0.2 (+ legacy API key)

## Consumer

| Hệ thống | Path |
|---|---|
| Web App | `clinic-booking/` |
| Spec | `clinic-booking/PHASE2_AI_INTAKE_DEV_SPEC_REV_0_2.md` |
| Persistence | `ai_extraction_runs` (không còn `ai_extraction_logs` 1-1) |

## Priorities

1. HMAC + error `retryable` taxonomy.
2. Zero PII trong log; redact SĐT/CCCD trong OCR text.
3. `bbox_norm` % trên coordinate_space=`derivative`.
4. Pass 2 nhận `verified_parameters` + `anonymous_patient_token`.
5. AI không chẩn đoán / kê thuốc.

## Ownership boundary

| Repo này | clinic-booking |
|---|---|
| `/v1/ocr/*`, `/v1/analyze/*` | Derivative, jobs, revisions, UI, Medical Matrix |

## Do not do

- Không tự chẩn đoán / gợi ý thuốc.
- Không log raw provider response có PII.
- Không trả public URL file.
- Không hard-code API key.
- Không phụ thuộc Laravel.
