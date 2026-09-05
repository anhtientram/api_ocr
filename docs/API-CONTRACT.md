# API Contract — AI Intake Proxy v1

Base URL (internal): `https://ai-intake.internal` (env `AI_PROXY_BASE_URL` phía clinic-booking).

Auth: header `X-AI-Proxy-Key: <secret>` (env `AI_PROXY_SECRET`).

## Endpoints

### `GET /health`

```json
{ "status": "ok", "ocr": "ready", "ai": "ready" }
```

### `POST /v1/ocr/extract`

OCR + AI bóc chỉ số từ 1 file (ảnh hoặc PDF).

**Request** (`multipart/form-data`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | binary | yes | png/jpg/jpeg/webp/pdf, max 15MB |
| `document_type` | string | yes | `lab` \| `ultrasound` \| `prescription` \| `other` |
| `language` | string | no | default `vie+eng` |
| `request_id` | string | no | idempotency / audit correlation |
| `include_bbox` | bool | no | default `true` — phục vụ Source Trace P2.04 |
| `include_summary` | bool | no | default `false` |

**Response 200**:

```json
{
  "request_id": "uuid",
  "document_type": "lab",
  "raw_ocr_text": "...",
  "ocr_confidence": 0.82,
  "extracted_parameters": [
    {
      "key": "amh",
      "label": "AMH",
      "value": 1.27,
      "unit": "ng/mL",
      "raw_text": "AMH: 1.27 ng/mL",
      "confidence": 0.91,
      "needs_human_verify": false,
      "page": 0,
      "bbox": { "x": 120, "y": 340, "w": 180, "h": 28 }
    }
  ],
  "source_trace_map": {
    "amh": { "page": 0, "bbox": { "x": 120, "y": 340, "w": 180, "h": 28 } }
  },
  "ai_summary_30s": null,
  "usage": {
    "ocr_ms": 1200,
    "ai_ms": 800,
    "prompt_tokens": 400,
    "completion_tokens": 120,
    "model": "gpt-4.1-mini"
  },
  "warnings": []
}
```

**Errors** (4xx/5xx, luôn JSON):

```json
{
  "error": {
    "code": "OCR_FAILED | AI_FAILED | INVALID_FILE | UNAUTHORIZED | RATE_LIMITED",
    "message": "human-readable, no PII",
    "request_id": "uuid"
  }
}
```

### `POST /v1/analyze/summary`

Tóm tắt 30s từ payload đã anonymize (P2.05). Không nhận file PII.

**Request** (`application/json`):

```json
{
  "request_id": "uuid",
  "layer1_clinical_notes": { "medical_history": "...", "allergies": "...", "current_medications": "..." },
  "layer2_clinical_data": {},
  "extracted_parameters": [],
  "document_hints": ["lab", "ultrasound"]
}
```

**Response 200**:

```json
{
  "request_id": "uuid",
  "ai_summary_30s": "Bệnh nhân … Chỉ số AMH 1.27 ng/mL …",
  "usage": { "prompt_tokens": 600, "completion_tokens": 180, "model": "..." }
}
```

Post-filter: strip câu kiểu chẩn đoán / kê đơn nếu model tràn.

## Versioning

- Breaking change → `/v2/...`
- Additive fields OK trong cùng major.
