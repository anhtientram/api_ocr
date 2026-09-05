# OCR Pipeline Rules

## Engine
- Default: **Tesseract** `vie+eng`
- PDF: convert từng trang → ảnh (Poppler / pdf2image), OCR từng trang, gộp
- Ảnh: preprocess nhẹ (grayscale, contrast) trước OCR; tránh pipeline nặng

## Limits
- Max file 15MB; max 20 pages/PDF (config)
- Timeout OCR per page; fail partial → vẫn trả trang đã đọc + `warnings`

## Output
- Luôn có `raw_ocr_text` + `ocr_confidence` (trung bình có trọng số)
- Không tự “sửa” số liệu y tế bằng heuristic mơ hồ — để AI extract có confidence

## Fallback
- OCR empty / confidence < ngưỡng → vẫn gọi AI nếu còn text thô; nếu không → `OCR_FAILED` có cấu trúc
