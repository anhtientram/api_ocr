---
name: implement-ocr-endpoint
description: Scaffold FastAPI endpoint OCR ảnh/PDF bằng Tesseract, khớp contract /v1/ocr/extract.
---

# Implement OCR Endpoint

- **Maps to:** clinic-booking P2.03 (phần OCR)
- **Contract:** `docs/API-CONTRACT.md` → `POST /v1/ocr/extract`
- **Rules:** `.agents/rules/10-ocr-pipeline.md`, `30-pii-and-security.md`

## Checklist

```
- [ ] FastAPI app + /health
- [ ] Auth X-AI-Proxy-Key
- [ ] Accept image + PDF
- [ ] Tesseract vie+eng
- [ ] PDF → images → OCR pages
- [ ] Return raw_ocr_text + ocr_confidence
- [ ] extracted_parameters = [] (nếu AI chưa làm)
- [ ] Temp file cleanup
- [ ] Dockerfile + tessdata
- [ ] Unit/integration test với fixture
```

## Steps

1. Tạo cấu trúc `app/` (api, services/ocr, core/config).
2. Implement `OcrService.extract(file) -> { text, confidence, pages[] }`.
3. Endpoint validate `document_type`, MIME, size.
4. Không gọi AI ở bước này nếu đang tách PR — vẫn trả schema đầy đủ với list rỗng.
5. Test: PNG chữ rõ → text; PDF 2 trang → gộp; file hỏng → `INVALID_FILE`.

## Acceptance

- Call multipart trả 200 + `raw_ocr_text` không rỗng trên fixture tiếng Việt.
- Secret sai → 401 `UNAUTHORIZED`.
