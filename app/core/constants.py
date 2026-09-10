from __future__ import annotations

from enum import Enum


class DocumentType(str, Enum):
    lab = "lab"
    ultrasound = "ultrasound"
    prescription = "prescription"
    other = "other"


class ErrorCode(str, Enum):
    OCR_FAILED = "OCR_FAILED"
    AI_FAILED = "AI_FAILED"
    INVALID_FILE = "INVALID_FILE"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMITED = "RATE_LIMITED"
    PII_REJECTED = "PII_REJECTED"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    RATE_LIMIT = "RATE_LIMIT"
    UNSUPPORTED_IMAGE = "UNSUPPORTED_IMAGE"
    HMAC_INVALID = "HMAC_INVALID"
    HMAC_EXPIRED = "HMAC_EXPIRED"


# Which error codes Laravel jobs should retry (exponential backoff, max 3).
RETRYABLE_ERROR_CODES: frozenset[str] = frozenset(
    {
        ErrorCode.PROVIDER_TIMEOUT.value,
        ErrorCode.RATE_LIMITED.value,
        ErrorCode.RATE_LIMIT.value,
        ErrorCode.AI_FAILED.value,
        ErrorCode.OCR_FAILED.value,
    }
)

NON_RETRYABLE_ERROR_CODES: frozenset[str] = frozenset(
    {
        ErrorCode.INVALID_FILE.value,
        ErrorCode.UNAUTHORIZED.value,
        ErrorCode.HMAC_INVALID.value,
        ErrorCode.HMAC_EXPIRED.value,
        ErrorCode.UNSUPPORTED_IMAGE.value,
        ErrorCode.PII_REJECTED.value,
    }
)


def is_retryable(code: str | ErrorCode) -> bool:
    value = code.value if isinstance(code, ErrorCode) else code
    if value in NON_RETRYABLE_ERROR_CODES:
        return False
    if value in RETRYABLE_ERROR_CODES:
        return True
    return False
