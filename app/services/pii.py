from __future__ import annotations

import re

# Vietnamese mobile/landline-ish patterns (10–11 digits starting with 0)
PHONE_RE = re.compile(r"(?<!\d)0\d{8,10}(?!\d)")
# Loose address cues — used only for redaction hint, not rejection
ADDRESS_HINT_RE = re.compile(r"(?i)\b(địa chỉ|dia chi|address)\s*[:：]")


def find_pii_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for m in PHONE_RE.finditer(text or ""):
        spans.append((m.start(), m.end(), "phone"))
    return spans


def redact_pii(text: str) -> tuple[str, bool]:
    """Return redacted text and whether any PII was found."""
    if not text:
        return text, False
    found = False

    def _mask(m: re.Match[str]) -> str:
        nonlocal found
        found = True
        s = m.group(0)
        if len(s) <= 4:
            return "***"
        return s[:3] + "***" + s[-3:]

    redacted = PHONE_RE.sub(_mask, text)
    return redacted, found
