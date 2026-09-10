# API Contract — AI Intake Proxy v1.1 (Phase 2 Rev 0.2)

Base URL (internal): `https://ai-intake.internal` (env `AI_PROXY_BASE_URL` phía clinic-booking).

## Auth

### Preferred — HMAC (Rev 0.2 §4.2)

```http
X-Clinic-Service: clinic-booking-core
X-Clinic-Timestamp: 1725872400
X-Clinic-Nonce: b8f3c1a2d5e4...
X-Clinic-Signature: hex(hmac_sha256(key=secret+timestamp+nonce, msg=raw_body))
```

- Timestamp skew tối đa ±300s (chống replay).
- Body = raw HTTP body (multipart hoặc JSON).

### Legacy (transition)

```http
X-AI-Proxy-Key: <AI_PROXY_SECRET>
```

## Endpoints

### `GET /health`

```json
{ "status": "ok", "ocr": "ready", "ai": "ready" }
```

### `POST /v1/ocr/extract`

OCR + AI bóc chỉ số từ 1 file **derivative** (đã orient/redact PII phía clinic-booking).

**Request** (`multipart/form-data`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | binary | yes | png/jpg/jpeg/webp/pdf, max 15MB |
| `document_type` | string | yes | `lab` \| `ultrasound` \| `prescription` \| `other` |
| `language` | string | no | default `vie+eng` |
| `request_id` | string | no | maps to `correlation_id` / audit |
| `include_bbox` | bool | no | default `true` — Source Trace |
| `include_summary` | bool | no | default `false` |

**Response 200**:

```json
{
  "request_id": "uuid",
  "document_type": "lab",
  "raw_ocr_text": "...",
  "ocr_confidence": 0.82,
  "coordinate_space": "derivative",
  "page_geometry": [
    { "page": 0, "width": 1200, "height": 1600, "coordinate_space": "derivative" }
  ],
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
      "bbox": { "x": 120, "y": 340, "w": 180, "h": 28 },
      "bbox_norm": { "x_pct": 10.0, "y_pct": 21.25, "w_pct": 15.0, "h_pct": 1.75 }
    }
  ],
  "source_trace_map": {
    "amh": {
      "page": 0,
      "bbox": { "x": 120, "y": 340, "w": 180, "h": 28 },
      "bbox_norm": { "x_pct": 10.0, "y_pct": 21.25, "w_pct": 15.0, "h_pct": 1.75 },
      "coordinate_space": "derivative",
      "page_width": 1200,
      "page_height": 1600
    }
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

Alpine Source Trace **phải** dùng `bbox_norm` (% trên derivative).

**Errors** (4xx/5xx, luôn JSON):

```json
{
  "error": {
    "code": "PROVIDER_TIMEOUT | RATE_LIMIT | UNSUPPORTED_IMAGE | OCR_FAILED | AI_FAILED | INVALID_FILE | UNAUTHORIZED | HMAC_INVALID | HMAC_EXPIRED | RATE_LIMITED",
    "message": "human-readable, no PII",
    "request_id": "uuid",
    "retryable": true
  }
}
```

`retryable=true` → Laravel job retry tối đa 3 lần (backoff).  
Non-retry: `INVALID_FILE`, `UNAUTHORIZED`, `HMAC_*`, `UNSUPPORTED_IMAGE`, `PII_REJECTED`.

### `POST /v1/analyze/summary`

Pass 2 — tóm tắt 30s từ **B2 verified revision** (anonymize). Không nhận file PII.

**Request** (`application/json`):

```json
{
  "request_id": "uuid",
  "correlation_id": "corr-8912",
  "anonymous_patient_token": "PT-09283-X",
  "verified_parameters": { "amh": 1.72, "fsh": 6.5 },
  "b2_clinical_notes": "...",
  "extracted_parameters": [],
  "document_hints": ["lab", "ultrasound"]
}
```

Deprecated (vẫn nhận): `layer1_clinical_notes`, `layer2_clinical_data`.

**Response 200**:

```json
{
  "request_id": "uuid",
  "correlation_id": "corr-8912",
  "anonymous_patient_token": "PT-09283-X",
  "ai_summary_30s": "… Chỉ số AMH 1.72 ng/mL …",
  "usage": { "prompt_tokens": 600, "completion_tokens": 180, "model": "..." }
}
```

Post-filter: strip câu kiểu chẩn đoán / kê đơn nếu model tràn.

## Versioning

- Breaking change → `/v2/...`
- Additive fields OK trong cùng major (`bbox_norm`, `page_geometry`, HMAC, `retryable`).
