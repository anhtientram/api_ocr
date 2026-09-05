---
name: review-before-merge
description: Checklist review trước khi merge thay đổi api_ocr.
---

# Review Before Merge

Làm theo `.agents/rules/50-code-review.md` cộng thêm:

1. Diff có đụng prompt/schema? → cập nhật `docs/API-CONTRACT.md` nếu additive.
2. Có secret/hard-coded key không?
3. Dockerfile còn đủ `tesseract-ocr-vie` + `poppler-utils`?
4. Test fixture AMH còn pass?
5. Không thêm dependency nặng không cần (tránh kéo full VI-Translate / layout YOLO trừ khi có ADR).

Merge chỉ khi checklist xanh.
