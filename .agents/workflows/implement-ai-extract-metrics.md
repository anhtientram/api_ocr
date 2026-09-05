---
name: implement-ai-extract-metrics
description: Thêm lớp AI structured extract chỉ số lab/ultrasound từ raw OCR; cấm chẩn đoán.
---

# Implement AI Extract Metrics

- **Maps to:** clinic-booking P2.03 acceptance “bóc chỉ số AMH…”
- **Rules:** `.agents/rules/20-ai-analysis-rules.md`
- **Skill:** `.agents/skills/medical-lab-ocr/SKILL.md`

## Checklist

```
- [ ] Prompt versioned + JSON schema
- [ ] Post-filter cấm chẩn đoán/kê thuốc
- [ ] Map keys chuẩn (amh, fsh, …)
- [ ] confidence + needs_human_verify
- [ ] usage tokens/model
- [ ] AI timeout → AI_FAILED, không treo
- [ ] Fixture AMH 1.27 ng/mL
```

## Steps

1. `AiExtractService` nhận `raw_ocr_text` + `document_type` → `extracted_parameters[]`.
2. System prompt: chỉ extract; cấm diagnose/prescribe.
3. Normalize unit (vd `ng/ml` → `ng/mL`).
4. Threshold: confidence < 0.7 → `needs_human_verify: true`.
5. Test: fixture AMH; text có “nên dùng thuốc X” → không xuất hiện trong fields phụ.

## Acceptance

- Response có `extracted_parameters` với `key=amh`, `value≈1.27`, `unit=ng/mL`.
- Không có field diagnosis/medication_recommendation.
