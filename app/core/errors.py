from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.constants import ErrorCode


class AppError(Exception):
    def __init__(self, code: ErrorCode | str, message: str, status_code: int = 400, request_id: str | None = None):
        self.code = code.value if isinstance(code, ErrorCode) else code
        self.message = message
        self.status_code = status_code
        self.request_id = request_id
        super().__init__(message)


def error_body(code: str, message: str, request_id: str | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message, exc.request_id),
    )


async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    code = ErrorCode.UNAUTHORIZED.value if exc.status_code == 401 else "HTTP_ERROR"
    message = detail if isinstance(detail, str) else "Request failed"
    return JSONResponse(status_code=exc.status_code, content=error_body(code, message))
