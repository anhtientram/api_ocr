---
name: medical-lab-ocr
description: >-
  Extracts Vietnamese medical lab and ultrasound metrics (AMH, FSH, LH, E2, endometrium, etc.)
  from OCR text into structured JSON. Use when implementing AI extract prompts, normalizing
  units, confidence thresholds, or lab fixture tests for infertility/gynecology documents.
---

# Medical Lab OCR Skill

## Use when
- Viết/sửa prompt extract chỉ số
- Thêm key lab mới
- Fixture phiếu xét nghiệm / siêu âm tiếng Việt

## Document types
| type | Focus |
|---|---|
| `lab` | Hormone, máu, tinh dịch đồ |
| `ultrasound` | Niêm mạc, nang, kích thước u |
| `prescription` | Chỉ đọc text thuốc **đã kê sẵn** — không gợi ý thêm |
| `other` | Extract generic key/value nếu rõ |

## Canonical keys (normalize về snake_case)

| key | Aliases OCR thường gặp | unit mặc định |
|---|---|---|
| `amh` | AMH, Anti-Müllerian | ng/mL |
| `fsh` | FSH | mIU/mL |
| `lh` | LH | mIU/mL |
| `e2` | E2, Estradiol, Estradiol (E2) | pg/mL |
| `progesterone` | Progesterone, P4 | ng/mL |
| `prolactin` | Prolactin, PRL | ng/mL |
| `tsh` | TSH | µIU/mL |
| `endometrium_mm` | Niêm mạc, Độ dày NMTC | mm |

Thêm key mới: cập nhật bảng này + schema + test.

## Output item shape

```json
{
  "key": "amh",
  "label": "AMH",
  "value": 1.27,
  "unit": "ng/mL",
  "raw_text": "AMH: 1.27 ng/mL",
  "confidence": 0.91,
  "needs_human_verify": false,
  "page": 0,
  "bbox": { "x": 0, "y": 0, "w": 0, "h": 0 }
}
```

## Rules
- Số không parse được → `value: null`, `needs_human_verify: true`, giữ `raw_text`.
- Không suy ra chỉ số không có trong text.
- Không đổi ý nghĩa lâm sàng (chỉ normalize format/unit).

## Fixtures
Ưu tiên ảnh/PDF mẫu không PII (che tên/SĐT). Acceptance P2.03: AMH `1.27` ng/mL.
