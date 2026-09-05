---
name: implement-ai-summary
description: Endpoint tóm tắt 30s từ payload anonymize; post-filter chẩn đoán.
---

# Implement AI Summary 30s

- **Maps to:** clinic-booking P2.05
- **Endpoint:** `POST /v1/analyze/summary`
- **Optional:** `include_summary=true` trên `/v1/ocr/extract`

## Checklist

```
- [ ] Chỉ nhận JSON anonymize (không file bắt buộc)
- [ ] Output ≤ ~120–180 từ tiếng Việt
- [ ] Post-filter diagnosis/prescription phrases
- [ ] Fail → AI_FAILED; Web App vẫn chạy thủ công
- [ ] usage tokens ghi nhận
```

## Steps

1. Prompt: tóm tắt facts từ layer notes + extracted params; cấm kết luận lâm sàng.
2. Reject nếu body chứa SĐT pattern rõ.
3. Test snapshot: không chứa “chẩn đoán”, “kê đơn”, “nên dùng”.

## Acceptance

- Summary ngắn, nêu chỉ số đã extract; không tư vấn điều trị.
