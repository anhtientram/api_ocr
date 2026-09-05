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
