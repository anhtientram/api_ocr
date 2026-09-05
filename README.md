# api_ocr — AI Intake Proxy

API nội bộ để **clinic-booking** gọi OCR + AI phân tích ảnh/PDF phiếu xét nghiệm (Phase 2).

## Quick start

```bash
cd api_ocr
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# macOS: brew install tesseract tesseract-lang poppler
# Ubuntu: apt install tesseract-ocr tesseract-ocr-vie poppler-utils

uvicorn app.main:app --reload --port 8080
```

Health: `GET http://127.0.0.1:8080/health`

## Test API

### Swagger (khuyên dùng)
1. Chạy server: `uvicorn app.main:app --reload --port 8080`
2. Mở [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
3. Bấm **Authorize** → dán `dev-secret-change-me` (hoặc `AI_PROXY_SECRET` trong `.env`)
4. Thử `POST /v1/ocr/extract` → chọn file ảnh/PDF

ReDoc: [http://127.0.0.1:8080/redoc](http://127.0.0.1:8080/redoc)  
OpenAPI raw: [http://127.0.0.1:8080/openapi.json](http://127.0.0.1:8080/openapi.json)

### Postman
Import 2 file trong `docs/postman/`:
- `ai_intake_proxy.postman_collection.json`
- `ai_intake_proxy.local.postman_environment.json` (chọn environment **api_ocr Local**)

Request **Extract**: chọn file ở field `file` rồi Send.

## Auth

Mọi `/v1/*` cần header:

```http
X-AI-Proxy-Key: <AI_PROXY_SECRET>
```

## Endpoints

| Method | Path | Mô tả |
|---|---|---|
| GET | `/health` | OCR/AI readiness |
| POST | `/v1/ocr/extract` | Upload file → OCR + extract chỉ số JSON |
| POST | `/v1/analyze/summary` | Tóm tắt 30s từ payload anonymize |

Chi tiết: [`docs/API-CONTRACT.md`](docs/API-CONTRACT.md)

### Ví dụ extract

```bash
curl -X POST http://127.0.0.1:8080/v1/ocr/extract \
  -H "X-AI-Proxy-Key: dev-secret-change-me" \
  -F "file=@phieu_amh.png" \
  -F "document_type=lab" \
  -F "include_bbox=true"
```

Không có `AI_API_KEY` / `GEMINI_API_KEY` → dùng **heuristic** (AMH/FSH/LH/…).  

## Tiết kiệm token (mặc định)

| `EXTRACT_MODE` | Cách chạy | Token Gemini |
|---|---|---|
| **`free`** | Tesseract + hàng/cột + cắt cột (phiếu 2 cột) | **0** |
| `ocr` | OCR + Gemini text (không gửi ảnh) | Thấp |
| **`ocr_first`** (default) | OCR bảng trước; Vision chỉ khi thiếu chỉ số / OCR yếu | Tiết kiệm + đủ field |
| `vision` | Luôn Gemini Vision | Cao |

`.env` hiện tại: `EXTRACT_MODE=free` — 0 token; layout 2 cột dùng crop label/result.  
`include_summary=false` để khỏi tốn token tóm tắt.  
Watermark nặng vẫn có thể thiếu số (OCR không thấy chữ).

```env
EXTRACT_MODE=free
AI_PROVIDER=gemini
AI_API_KEY=your_gemini_key
AI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
AI_MODEL=gemini-2.5-flash
```

Lấy key tại [Google AI Studio](https://aistudio.google.com/apikey) (chỉ cần khi không dùng `free`).

## Docker

```bash
docker build -t api-ocr .
docker run --rm -p 8080:8080 -e AI_PROXY_SECRET=dev-secret-change-me api-ocr
```

## Tests

```bash
pytest -q
```

## Agent docs

`AGENTS.md` · `.agents/` · `.cursor/rules/` — skill/workflows cho agent implement tiếp.

## Consumer

Web App gọi service này qua `AiProxyClient` (chưa làm bên clinic-booking). Contract: `docs/CONTRACT-WITH-CLINIC-BOOKING.md`.
