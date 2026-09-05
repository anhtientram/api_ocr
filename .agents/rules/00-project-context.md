# Project Context — api_ocr

## Business
Microservice OCR + AI cho luồng **remote_prescription** của NTT: Sale upload phiếu xét nghiệm → hệ thống bóc chỉ số → B2 verify → B3 duyệt.

## Consumers
- `clinic-booking` Laravel app (AiProxyClient)
- Không expose public internet nếu chưa có API gateway + auth mạnh

## Outcomes
- Bóc AMH/FSH/… từ ảnh/PDF tiếng Việt
- Trả bbox cho Source Trace
- Tóm tắt 30s không chẩn đoán
- Usage metrics cho cost dashboard
