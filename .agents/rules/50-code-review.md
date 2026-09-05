# Code Review Rules

Trước merge:

- [ ] Schema response khớp `docs/API-CONTRACT.md`
- [ ] Có test fixture AMH (ảnh/PDF giả) → JSON đúng key/unit
- [ ] Proxy/AI timeout không làm worker treo; trả `AI_FAILED`
- [ ] Không log PII
- [ ] Prompt cấm chẩn đoán; có post-filter test
- [ ] File tạm được xoá
- [ ] Dockerfile cài Tesseract `vie` + Poppler
- [ ] README env vars đầy đủ
