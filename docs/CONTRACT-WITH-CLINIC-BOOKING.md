# Contract với clinic-booking (Phase 2 Rev 0.2)

Nguồn: `clinic-booking/PHASE2_AI_INTAKE_DEV_SPEC_REV_0_2.md`.

## Vai trò

```
Sale upload Tầng 3 (private/raw, SHA-256 bất biến)
    → CreateDerivativeImageAction (orient + redact header PII)
    → ai_extraction_runs (pass1_ocr) + ProcessAiOcrRunJob afterCommit
        → AiProxyHmacClient POST derivative → api_ocr /v1/ocr/extract
        → lưu ai_extracted_items + source_trace (bbox_norm %)
    → B2 verify → form_submission_verified_revisions (không đè layer2 B1)
    → acceptToB3 → GeneratePass2ClinicalSummaryJob
        → POST /v1/analyze/summary (verified_parameters + anonymous_patient_token)
```

## Ownership

| Repo `api_ocr` | Repo `clinic-booking` |
|---|---|
| OCR, extract, summary, bbox %, tokens, HMAC verify | Derivative, HMAC client, runs/revisions, UI, risk matrix |
| Không hard-gate y khoa | ClinicalRiskRuleEngine (sau chữ ký Mục 3) |

## Document types

| key | label VN |
|---|---|
| `lab` | Xét nghiệm |
| `ultrasound` | Siêu âm |
| `prescription` | Đơn thuốc |
| `other` | Khác |

## Auth

HMAC headers (`X-Clinic-*`) theo §4.2. Legacy `X-AI-Proxy-Key` chỉ transition.

## Mapping deliverable

| Task / Spec | Endpoint / field api_ocr |
|---|---|
| Pass 1 OCR | `POST /v1/ocr/extract` → `extracted_parameters`, `bbox_norm` |
| Source Trace | `source_trace_map.*.bbox_norm` + `page_geometry` |
| Pass 2 Summary | `POST /v1/analyze/summary` với `verified_parameters` |
| Cost dashboard | `usage.prompt_tokens`, `completion_tokens`, `model` |
| Retry | `error.retryable` + codes `PROVIDER_TIMEOUT`, `RATE_LIMIT`, … |

## Hard rules

- AI **không** chẩn đoán / kê thuốc.
- OCR fail không chặn B1→B2 (fallback manual).
- Không public URL file; bbox trên **derivative**, không raw.
- Cấm log raw OCR / provider body có PII.
- Persistence Web App: `ai_extraction_runs` (1-N), **không** ghi đè `layer2_clinical_data`.
