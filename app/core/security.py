from __future__ import annotations

from typing import Optional

from fastapi import Header, Request

from app.core.config import get_settings
from app.core.constants import ErrorCode
from app.core.errors import AppError


async def require_proxy_key(
    x_ai_proxy_key: Optional[str] = Header(default=None, alias="X-AI-Proxy-Key"),
) -> None:
    settings = get_settings()
    if not x_ai_proxy_key or x_ai_proxy_key != settings.ai_proxy_secret:
        raise AppError(ErrorCode.UNAUTHORIZED, "Invalid or missing X-AI-Proxy-Key", status_code=401)


def get_request_id(request: Request, explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit
    return getattr(request.state, "request_id", None) or request.headers.get("X-Request-Id") or ""
