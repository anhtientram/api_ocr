from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.main import create_app
from app.services.ocr import OcrResult, PageOcrResult
from app.services.bbox import WordBox


def _client(extract_mode: str = "ocr") -> TestClient:
    get_settings.cache_clear()
    import os

    os.environ["EXTRACT_MODE"] = extract_mode
    os.environ["RUN_OCR_WITH_VISION"] = "true"
    get_settings.cache_clear()
    return TestClient(create_app())


def test_health():
    r = _client().get("/health")
    assert r.status_code == 200
    assert "ocr" in r.json()


def test_unauthorized_extract():
    c = _client()
    r = c.post(
        "/v1/ocr/extract",
        data={"document_type": "lab"},
        files={"file": ("x.png", b"not-an-image", "image/png")},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_extract_with_mocked_ocr():
    settings = get_settings()
    fake = OcrResult(
        text="AMH: 1.27 ng/mL\nFSH 6.5 mIU/mL",
        confidence=0.9,
        pages=[
            PageOcrResult(
                page=0,
                text="AMH: 1.27 ng/mL\nFSH 6.5 mIU/mL",
                confidence=0.9,
                word_boxes=[
                    WordBox(text="AMH:", conf=0.9, page=0, left=10, top=20, width=40, height=12),
                    WordBox(text="1.27", conf=0.9, page=0, left=55, top=20, width=30, height=12),
                ],
            )
        ],
        ocr_ms=12,
    )

    img = Image.new("RGB", (200, 60), "white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    png = buf.getvalue()

    with patch("app.api.v1.routes.OcrService.extract", return_value=fake):
        c = _client()
        r = c.post(
            "/v1/ocr/extract",
            headers={"X-AI-Proxy-Key": settings.ai_proxy_secret},
            data={"document_type": "lab", "include_bbox": "true"},
            files={"file": ("amh.png", png, "image/png")},
        )

    assert r.status_code == 200, r.text
    body = r.json()
    keys = {p["key"] for p in body["extracted_parameters"]}
    assert "amh" in keys
    amh = next(p for p in body["extracted_parameters"] if p["key"] == "amh")
    assert amh["value"] == 1.27
    assert body["usage"]["model"] in {"heuristic", "gemini-2.5-flash", settings.ai_model}
    assert "amh" in body["source_trace_map"]


def test_summary_endpoint():
    settings = get_settings()
    c = _client()
    r = c.post(
        "/v1/analyze/summary",
        headers={"X-AI-Proxy-Key": settings.ai_proxy_secret},
        json={
            "layer1_clinical_notes": {"medical_history": "Hiếm muộn 2 năm", "allergies": "Không"},
            "extracted_parameters": [
                {
                    "key": "amh",
                    "label": "AMH",
                    "value": 1.27,
                    "unit": "ng/mL",
                    "confidence": 0.9,
                    "needs_human_verify": False,
                }
            ],
            "document_hints": ["lab"],
        },
    )
    assert r.status_code == 200, r.text
    assert "AMH" in r.json()["ai_summary_30s"] or "1.27" in r.json()["ai_summary_30s"]
