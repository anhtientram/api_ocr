from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.schemas import ExtractedParameter
from app.services.table_extract import recover_decimal


@dataclass(frozen=True)
class MetricDef:
    key: str
    label: str
    unit: str
    patterns: tuple[re.Pattern[str], ...]


def _p(*exprs: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(e, re.IGNORECASE | re.MULTILINE) for e in exprs)


# Prefer patterns that capture RESULT near the metric name, not reference ranges.
METRICS: tuple[MetricDef, ...] = (
    MetricDef("amh", "AMH", "ng/mL", _p(r"AMH\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)\s*(ng\s*/?\s*m[lL])?")),
    MetricDef("fsh", "FSH", "mIU/mL", _p(r"\bFSH\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("lh", "LH", "mIU/mL", _p(r"\bLH\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("e2", "Estradiol (E2)", "pg/mL", _p(r"\bE2\b\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)", r"Estradiol[^\d]{0,20}([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("glucose", "Glucose", "mmol/L", _p(r"Glucose\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)\s*(mmol)?")),
    MetricDef("urea", "Urê", "mmol/L", _p(r"Ur[eêé]\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)\s*(mmol)?")),
    MetricDef("creatinine", "Creatinin", "µmol/L", _p(r"Cr(?:e)?atinin\w*\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("cholesterol", "Cholesterol", "mmol/L", _p(r"Cholesterol\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("triglycerid", "Triglycerid", "mmol/L", _p(r"Triglycerid\w*\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("hdl", "HDL-cho", "mmol/L", _p(r"HDL[-\s]?cho\w*\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)", r"\bHDL\b\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("ldl", "LDL-cho", "mmol/L", _p(r"LDL[-\s]?cho\w*\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)", r"\bLDL\b\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("ggt", "GGT", "U/L", _p(r"\bGGT\b\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("ast", "AST (GOT)", "U/L", _p(r"AST\s*(?:\(GOT\))?\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)", r"\bGOT\b\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("alt", "ALT (GPT)", "U/L", _p(r"ALT\s*(?:\(GPT\))?\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)", r"\bGPT\b\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("uric_acid", "Acid Uric", "µmol/L", _p(r"Acid\s*Uric\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)", r"Uric\s*Acid\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("endometrium_mm", "Niêm mạc tử cung", "mm", _p(r"(?:niêm\s*mạc|niem\s*mac|endometr\w*)[^\d]{0,30}([0-9]+(?:[.,][0-9]+)?)\s*mm")),
    # Huyết học
    MetricDef(
        "rbc",
        "Số lượng HC",
        "T/L",
        _p(
            r"(?:Số\s*lượng\s*HC|hong\s*cau|hồng\s*cầu|RBC)\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)",
            r"HC\s*[:\|]\s*([0-9]+(?:[.,][0-9]+)?)",
        ),
    ),
    MetricDef(
        "hgb",
        "Huyết sắc tố",
        "g/L",
        _p(
            r"(?:Huyết\s*sắc\s*t[ốo]|Huyet\s*sac\s*to|Hemoglobin|\bHGB\b|\bHb\b)\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)",
        ),
    ),
    MetricDef(
        "hct",
        "Hematocrit",
        "L/L",
        _p(r"(?:Hematocrit|\bHct\b)\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)"),
    ),
    MetricDef(
        "plt",
        "Tiểu cầu",
        "G/L",
        _p(
            r"(?:Số\s*lượng\s*tiểu\s*cầu|tiểu\s*cầu|tieu\s*cau|Platelet|\bPLT\b)\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)",
        ),
    ),
    MetricDef(
        "wbc",
        "Số lượng BC",
        "G/L",
        _p(
            r"(?:Số\s*lượng\s*BC|bạch\s*cầu|bach\s*cau|\bWBC\b)\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)",
        ),
    ),
    MetricDef("mcv", "MCV", "fL", _p(r"\bMCV\b\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("mch", "MCH", "pg", _p(r"\bMCH\b\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
    MetricDef("mchc", "MCHC", "g/L", _p(r"\bMCHC\b\s*[:\|]?\s*([0-9]+(?:[.,][0-9]+)?)")),
)


def _to_float(raw: str) -> float | None:
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def heuristic_extract(ocr_text: str, document_type: str = "lab") -> list[ExtractedParameter]:
    """Offline extractor — 0 token. Best-effort on OCR text."""
    if not ocr_text or not ocr_text.strip():
        return []
    if document_type == "prescription":
        return []

    found: dict[str, ExtractedParameter] = {}
    for metric in METRICS:
        if document_type == "ultrasound" and metric.key not in {"endometrium_mm"}:
            continue
        for pattern in metric.patterns:
            m = pattern.search(ocr_text)
            if not m:
                continue
            value = _to_float(m.group(1))
            fixed = False
            if value is not None:
                value, fixed = recover_decimal(metric.key, value)
            conf = 0.72 if fixed else (0.8 if value is not None else 0.4)
            found[metric.key] = ExtractedParameter(
                key=metric.key,
                label=metric.label,
                value=value,
                unit=metric.unit,
                raw_text=m.group(0).strip()[:120],
                confidence=conf,
                needs_human_verify=fixed or value is None or conf < 0.7,
                page=0,
                bbox=None,
            )
            break
    return list(found.values())
