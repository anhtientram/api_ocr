from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional

from fastapi import Header, Request

from app.core.config import get_settings
from app.core.constants import ErrorCode
from app.core.errors import AppError

# Clock skew allowed for HMAC timestamp (seconds).
HMAC_MAX_SKEW_SECONDS = 300


def sign_payload(secret: str, timestamp: str, nonce: str, body: bytes) -> str:
    """Rev 0.2: sha256_hmac(body, secret + timestamp + nonce)."""
    key = f"{secret}{timestamp}{nonce}".encode("utf-8")
    return hmac.new(key, body, hashlib.sha256).hexdigest()


async def require_proxy_auth(
    request: Request,
    x_ai_proxy_key: Optional[str] = Header(default=None, alias="X-AI-Proxy-Key"),
    x_clinic_service: Optional[str] = Header(default=None, alias="X-Clinic-Service"),
    x_clinic_timestamp: Optional[str] = Header(default=None, alias="X-Clinic-Timestamp"),
    x_clinic_nonce: Optional[str] = Header(default=None, alias="X-Clinic-Nonce"),
    x_clinic_signature: Optional[str] = Header(default=None, alias="X-Clinic-Signature"),
    x_clinic_content_sha256: Optional[str] = Header(default=None, alias="X-Clinic-Content-Sha256"),
) -> None:
    """Accept HMAC (preferred, Rev 0.2) or legacy X-AI-Proxy-Key during transition."""
    settings = get_settings()
    secret = settings.ai_proxy_secret

    has_hmac = all([x_clinic_timestamp, x_clinic_nonce, x_clinic_signature])
    if has_hmac:
        await _verify_hmac(
            request,
            secret=secret,
            service=x_clinic_service,
            timestamp=x_clinic_timestamp or "",
            nonce=x_clinic_nonce or "",
            signature=x_clinic_signature or "",
            content_sha256=x_clinic_content_sha256,
        )
        return

    if x_ai_proxy_key and hmac.compare_digest(x_ai_proxy_key, secret):
        return

    raise AppError(
        ErrorCode.UNAUTHORIZED,
        "Missing HMAC headers or invalid X-AI-Proxy-Key",
        status_code=401,
        retryable=False,
    )


async def _verify_hmac(
    request: Request,
    *,
    secret: str,
    service: Optional[str],
    timestamp: str,
    nonce: str,
    signature: str,
    content_sha256: Optional[str],
) -> None:
    if not service:
        raise AppError(
            ErrorCode.HMAC_INVALID,
            "X-Clinic-Service is required with HMAC auth",
            status_code=401,
            retryable=False,
        )

    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise AppError(
            ErrorCode.HMAC_INVALID,
            "X-Clinic-Timestamp must be unix epoch seconds",
            status_code=401,
            retryable=False,
        ) from exc

    now = int(time.time())
    if abs(now - ts) > HMAC_MAX_SKEW_SECONDS:
        raise AppError(
            ErrorCode.HMAC_EXPIRED,
            "HMAC timestamp outside allowed skew window",
            status_code=401,
            retryable=False,
        )

    if len(nonce) < 8:
        raise AppError(
            ErrorCode.HMAC_INVALID,
            "X-Clinic-Nonce too short",
            status_code=401,
            retryable=False,
        )

    body = getattr(request.state, "cached_body", None)
    if body is None:
        body = await request.body()

    provided = signature.strip().lower()
    expected_body = sign_payload(secret, timestamp, nonce, body)
    if hmac.compare_digest(expected_body, provided):
        return

    # Multipart upload: client may sign sha256(file_bytes) instead of raw multipart envelope
    if content_sha256 and len(content_sha256) == 64:
        expected_hash = sign_payload(secret, timestamp, nonce, content_sha256.lower().encode("utf-8"))
        if hmac.compare_digest(expected_hash, provided):
            return

    raise AppError(
        ErrorCode.HMAC_INVALID,
        "Invalid X-Clinic-Signature",
        status_code=401,
        retryable=False,
    )


async def require_proxy_key(
    x_ai_proxy_key: Optional[str] = Header(default=None, alias="X-AI-Proxy-Key"),
) -> None:
    settings = get_settings()
    if not x_ai_proxy_key or not hmac.compare_digest(x_ai_proxy_key, settings.ai_proxy_secret):
        raise AppError(ErrorCode.UNAUTHORIZED, "Invalid or missing X-AI-Proxy-Key", status_code=401)


def get_request_id(request: Request, explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-Id") or ""
