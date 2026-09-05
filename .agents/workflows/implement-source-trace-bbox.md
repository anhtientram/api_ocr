---
name: implement-source-trace-bbox
description: Gắn bbox/page cho từng chỉ số để clinic-booking Source Trace (P2.04).
---

# Implement Source Trace BBox

- **Maps to:** clinic-booking P2.04
- **Contract fields:** `bbox`, `source_trace_map`

## Checklist

```
- [ ] include_bbox=true trả bbox
- [ ] page 0-based
- [ ] source_trace_map[key] = { page, bbox }
- [ ] Thiếu bbox → param vẫn trả, map bỏ key đó (không crash)
- [ ] Toạ độ trên ảnh trang đã OCR (không phải PDF crop mơ hồ)
```

## Steps

1. Khi OCR, giữ word/line boxes từ Tesseract (TSV / image_to_data).
2. AI trả `raw_text` snippet → fuzzy match về line có bbox gần nhất.
3. Nếu không match → `bbox: null`, warning `bbox_unresolved`.
4. Test: click-map AMH trỏ đúng vùng (assert bbox overlap fixture annotation).

## Acceptance

- Fixture có annotation → IoU bbox ≥ ngưỡng tối thiểu hoặc nằm trong vùng kỳ vọng.
