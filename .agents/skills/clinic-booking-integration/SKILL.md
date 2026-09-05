---
name: clinic-booking-integration
description: >-
  Integrates api_ocr with the NTT clinic-booking Web App AI intake flow (Form Tier 3,
  AiProxyClient, OcrReaderService, Source Trace, Summary 30s). Use when aligning fields
  with clinic-booking tasks P2.01–P2.09 or FormIntake DOCUMENT_TYPES.
---

# Clinic-booking Integration Skill

## Use when
- Đồng bộ field với Laravel `AiProxyClient` / `OcrReaderService`
- Debug OCR không hiện trên B2 split view
- Thêm document type / cost usage cho dashboard

## Read first
- `docs/CONTRACT-WITH-CLINIC-BOOKING.md`
- `clinic-booking/tasks.json` (P2.*)
- `clinic-booking/.agents/workflows/dev2/dev2-p2.03-ocr-reader.md`
- `clinic-booking/.agents/workflows/dev2/dev2-p2.04-source-trace.md`
- `clinic-booking/.agents/workflows/dev2/dev2-p2.05-ai-summary-30s.md`
- `clinic-booking/docs/architecture/form-3-tier.md`
- `clinic-booking/docs/QUYET_DINH_GIAI_PHAP_PHASE_1.md` (cấm AI chẩn đoán)

## Ownership
| Việc | Repo |
|---|---|
| Anonymize PII, client, UI, risk flags, fallback | clinic-booking |
| OCR, AI extract, bbox, summary, token usage | api_ocr |

## Integration checklist
- [ ] `DOCUMENT_TYPES` khớp
- [ ] `extracted_parameters` + `raw_ocr_text` + `source_trace_map`
- [ ] `usage` cho P2.09
- [ ] Error codes client map được → không 500 form
- [ ] Secret key quay vòng được qua env
