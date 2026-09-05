# Workflows Index — api_ocr

Thứ tự triển khai khuyến nghị:

```text
1. Scaffold FastAPI + Docker + Tesseract
2. implement-ocr-endpoint          → POST /v1/ocr/extract (OCR only trước)
3. implement-ai-extract-metrics    → AI JSON chỉ số + confidence
4. implement-source-trace-bbox     → bbox / source_trace_map
5. implement-ai-summary            → /v1/analyze/summary
6. integrate-with-clinic-booking   → khớp AiProxyClient + fixture E2E
7. review-before-merge
```

| Workflow | Mục đích |
|---|---|
| `implement-ocr-endpoint.md` | FastAPI + Tesseract + PDF |
| `implement-ai-extract-metrics.md` | AI bóc AMH/FSH/… |
| `implement-source-trace-bbox.md` | bbox cho P2.04 |
| `implement-ai-summary.md` | Summary 30s P2.05 |
| `integrate-with-clinic-booking.md` | Contract với Web App |
| `review-before-merge.md` | Checklist merge |
