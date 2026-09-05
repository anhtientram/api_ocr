# Contract với clinic-booking

Nguồn yêu cầu: Excel gói thầu Phase 2 + `clinic-booking/tasks.json` + `.cursorrules` Web App.

## Vai trò

```
Sale upload Tầng 3 (private)
    → B2/Job kích hoạt OCR
        → clinic-booking: PiiAnonymizer (P2.02) strip SĐT/tên/địa chỉ
        → AiProxyClient (P2.01) POST file anonymized → api_ocr
        → OcrReaderService (P2.03) lưu ai_extraction_logs
        → SourceTraceViewer (P2.04) dùng source_trace_map
        → AiSummaryService (P2.05) có thể gọi /v1/analyze/summary
```

## Document types (khớp FormIntakeService)

| key | label VN |
|---|---|
| `lab` | Xét nghiệm |
| `ultrasound` | Siêu âm |
| `prescription` | Đơn thuốc |
| `other` | Khác |

## Chỉ số ưu tiên (lab / infertility)

`amh`, `fsh`, `lh`, `e2` (estradiol), `progesterone`, `prolactin`, `tsh`, tinh dịch đồ (nếu có), độ dày niêm mạc (ultrasound).

## 3 lớp dữ liệu (Web App P2.07 — proxy chỉ trả lớp AI)

1. Raw (khách khai) — Web App
2. **AI Extracted** — response `extracted_parameters` của repo này
3. Human Verified — B2 sửa trên UI — Web App

## Hard rules từ Web App

- AI **không** chẩn đoán / kê thuốc (`docs/QUYET_DINH_GIAI_PHAP_PHASE_1.md`).
- OCR fail không chặn B1→B2 (fallback P2.08).
- Không public URL file; bbox chỉ toạ độ relative trên trang.
- Cost/token trả trong `usage` để dashboard P2.09 aggregate.

## Mapping deliverable

| Task Web App | Endpoint / field api_ocr |
|---|---|
| P2.03 OCR Reader | `POST /v1/ocr/extract` → `extracted_parameters`, `raw_ocr_text` |
| P2.04 Source Trace | `source_trace_map` / `bbox` |
| P2.05 Summary 30s | `include_summary` hoặc `POST /v1/analyze/summary` |
| P2.09 Cost dashboard | `usage.prompt_tokens`, `completion_tokens`, `model` |
