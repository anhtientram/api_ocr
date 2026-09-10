from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.v1.routes import router as v1_router
from app.core.body_cache import BodyCacheMiddleware
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, http_error_handler
from app.services.ai import AiService

API_DESCRIPTION = """
AI Intake Proxy — OCR + extract chỉ số phiếu xét nghiệm (Phase 2 Rev 0.2).

## Auth (ưu tiên HMAC)
```
X-Clinic-Service: clinic-booking-core
X-Clinic-Timestamp: <unix>
X-Clinic-Nonce: <random>
X-Clinic-Signature: sha256_hmac(body, secret + timestamp + nonce)
```

Legacy transition: `X-AI-Proxy-Key: <AI_PROXY_SECRET>` vẫn được chấp nhận.
"""


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI Intake Proxy (api_ocr)",
        version="1.1.0",
        description=API_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(BodyCacheMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
    app.include_router(v1_router, tags=["v1"])

    @app.get("/health", tags=["ops"], summary="Health check")
    def health():
        ai = AiService(settings)
        ocr_status = "ready"
        try:
            from app.services import rapid_ocr

            if rapid_ocr.available():
                ocr_status = "ready"
            else:
                import pytesseract

                pytesseract.get_tesseract_version()
        except Exception:
            ocr_status = "unavailable"

        return {
            "status": "ok" if ocr_status == "ready" else "degraded",
            "ocr": ocr_status,
            "ai": "ready" if ai.available else "heuristic",
            "ai_provider": settings.ai_provider,
            "ai_model": settings.ai_model if ai.available else None,
        }

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        comps = schema.setdefault("components", {}).setdefault("securitySchemes", {})
        comps["AiProxyKey"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-AI-Proxy-Key",
            "description": "Legacy secret (env AI_PROXY_SECRET). Prefer HMAC headers.",
        }
        comps["ClinicHmac"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-Clinic-Signature",
            "description": "HMAC SHA-256 of body with key=secret+timestamp+nonce",
        }
        for path, methods in schema.get("paths", {}).items():
            if not path.startswith("/v1"):
                continue
            for op in methods.values():
                if isinstance(op, dict):
                    op.setdefault("security", [{"AiProxyKey": []}, {"ClinicHmac": []}])
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app


app = create_app()
