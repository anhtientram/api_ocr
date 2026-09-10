from __future__ import annotations

import re

# Vietnamese mobile/landline-ish patterns (10–11 digits starting with 0)
PHONE_RE = re.compile(r"(?<!\d)0\d{8,10}(?!\d)")
# CCCD / CMND style 9 or 12 digit national IDs (Rev 0.2 §4.3)
CCCD_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
CMND_RE = re.compile(r"(?<!\d)\d{9}(?!\d)")
# Loose address cues — used only for redaction hint, not rejection
ADDRESS_HINT_RE = re.compile(r"(?i)\b(địa chỉ|dia chi|address)\s*[:：]")
NAME_HINT_RE = re.compile(
    r"(?i)\b(họ\s*và\s*tên|ho\s*va\s*ten|họ\s*tên|ho\s*ten|patient\s*name|full\s*name)\s*[:：]\s*([^\n\r,]{2,80})"
)


def find_pii_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for m in PHONE_RE.finditer(text or ""):
        spans.append((m.start(), m.end(), "phone"))
    for m in CCCD_RE.finditer(text or ""):
        spans.append((m.start(), m.end(), "cccd"))
    for m in CMND_RE.finditer(text or ""):
        # Avoid double-counting digits already covered as phone/cccd
        if any(s <= m.start() < e for s, e, _ in spans):
            continue
        spans.append((m.start(), m.end(), "cmnd"))
    return spans


def _mask_digits(s: str) -> str:
    if len(s) <= 4:
        return "***"
    return s[:3] + "***" + s[-3:]


def redact_pii(text: str) -> tuple[str, bool]:
    """Return redacted text and whether any PII was found."""
    if not text:
        return text, False
    found = False

    def _mask_phone(m: re.Match[str]) -> str:
        nonlocal found
        found = True
        return _mask_digits(m.group(0))

    def _mask_id(m: re.Match[str]) -> str:
        nonlocal found
        found = True
        return _mask_digits(m.group(0))

    def _mask_name(m: re.Match[str]) -> str:
        nonlocal found
        found = True
        return f"{m.group(1)}: ***"

    redacted = PHONE_RE.sub(_mask_phone, text)
    redacted = CCCD_RE.sub(_mask_id, redacted)
    redacted = CMND_RE.sub(_mask_id, redacted)
    redacted = NAME_HINT_RE.sub(_mask_name, redacted)
    return redacted, found
