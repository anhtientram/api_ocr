---
name: integrate-with-clinic-booking
description: Khớp contract với AiProxyClient / OcrReaderService của clinic-booking.
---

# Integrate with clinic-booking

## Đọc trước

- `docs/CONTRACT-WITH-CLINIC-BOOKING.md`
- `clinic-booking/.agents/workflows/dev2/dev2-p2.03-ocr-reader.md`
- `clinic-booking/app/Domain/Prescriptions/FormIntakeService.php` → `DOCUMENT_TYPES`
- `clinic-booking/tasks.json` P2.01–P2.05, P2.09

## Checklist

```
- [ ] Enum document_type khớp 4 giá trị Web App
- [ ] Field names khớp AiProxyClient (khi Dev 1 viết — đồng bộ docs)
- [ ] usage đủ cho P2.09
- [ ] source_trace_map đủ cho P2.04
- [ ] Postman/OpenAPI mẫu trong docs/
- [ ] .env.example: AI_PROXY_SECRET, AI model keys
- [ ] Ghi chú: Web App anonymize trước khi gọi
```

## Steps

1. So schema response với deliverable `OcrReaderService` / `ai_extraction_logs`.
2. Chạy smoke từ machine Web App (curl) với secret staging.
3. Xác nhận fail modes: timeout không 500 form phía Laravel (trách nhiệm client + đúng error JSON).

## Acceptance

- Dev 2 P2.03 có thể lưu `extracted_parameters` + `raw_ocr_output` không map tay lệch field.
