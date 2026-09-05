---
name: api-ocr-microservice
description: >-
  Implements and reviews the AI Intake OCR proxy microservice (FastAPI + Tesseract + AI).
  Use when building OCR endpoints, AI extract/summary, Docker deploy, or changing
  docs/API-CONTRACT.md for api_ocr.
---

# API OCR Microservice Skill

## Use when
- Scaffold hoặc sửa FastAPI OCR service
- Đổi contract `/v1/ocr/extract` hoặc `/v1/analyze/summary`
- Docker/Tesseract/Poppler setup
- Auth secret / usage metrics

## Ground rules
1. Đọc `AGENTS.md` + `docs/API-CONTRACT.md` trước.
2. Consumer là `clinic-booking` Phase 2 (P2.03–P2.05, P2.09).
3. AI không chẩn đoán / không kê thuốc.
4. Zero PII trong log.
5. Schema ổn định; breaking → v2.

## Core artifacts
- `docs/API-CONTRACT.md`
- `docs/CONTRACT-WITH-CLINIC-BOOKING.md`
- `.agents/rules/*`
- `.agents/workflows/*`

## Deliverable checklist
- [ ] Endpoint + auth
- [ ] OCR vie+eng
- [ ] AI extract JSON
- [ ] usage tokens
- [ ] temp cleanup
- [ ] tests + Dockerfile
- [ ] contract docs updated
