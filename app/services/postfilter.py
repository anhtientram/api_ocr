from __future__ import annotations

import re

from app.models.schemas import ExtractedParameter

# Forbidden clinical advice patterns for post-filter
DIAGNOSIS_RE = re.compile(
    r"(?i)\b("
    r"chẩn\s*đoán|chan\s*doan|diagnosis|"
    r"kê\s*đơn|ke\s*don|kê\s*thuốc|prescrib|"
    r"nên\s*dùng|nen\s*dung|nên\s*uống|"
    r"khuyến\s*nghị\s*điều\s*trị|recommend(ed)?\s+treatment|"
    r"bác\s*sĩ\s*nên|doctor\s+should"
    r")\b"
)

UNIT_NORMALIZE = {
    "ng/ml": "ng/mL",
    "ng/ml.": "ng/mL",
    "miu/ml": "mIU/mL",
    "miu/mL": "mIU/mL",
    "pg/ml": "pg/mL",
    "uiu/ml": "µIU/mL",
    "µiu/ml": "µIU/mL",
    "uiu/mL": "µIU/mL",
}


def normalize_unit(unit: str | None) -> str | None:
    if not unit:
        return unit
    key = unit.strip()
    lower = key.lower().replace(" ", "")
    return UNIT_NORMALIZE.get(lower, key)


def strip_clinical_advice(text: str) -> str:
    if not text:
        return text
    lines = []
    for line in text.splitlines():
        if DIAGNOSIS_RE.search(line):
            continue
        lines.append(line)
    cleaned = "\n".join(lines).strip()
    # Also scrub inline phrases in single-paragraph summaries
    cleaned = DIAGNOSIS_RE.sub("[đã loại]", cleaned)
    return cleaned


def apply_verify_threshold(params: list[ExtractedParameter], threshold: float) -> list[ExtractedParameter]:
    out: list[ExtractedParameter] = []
    for p in params:
        data = p.model_dump()
        data["unit"] = normalize_unit(p.unit)
        if p.confidence < threshold or p.value is None:
            data["needs_human_verify"] = True
        out.append(ExtractedParameter(**data))
    return out
