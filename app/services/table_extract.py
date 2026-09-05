from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.schemas import ExtractedParameter
from app.services.bbox import WordBox

# Typical physiologic ranges used only to recover lost decimals (4.87 → 487).
TYPICAL_RANGE: dict[str, tuple[float, float]] = {
    "amh": (0.01, 20),
    "fsh": (0.1, 200),
    "lh": (0.1, 200),
    "e2": (1, 5000),
    "glucose": (1.5, 40),
    "urea": (1, 40),
    "creatinine": (20, 1500),
    "cholesterol": (1.5, 15),
    "triglycerid": (0.2, 25),
    "hdl": (0.2, 5),
    "ldl": (0.5, 12),
    "ggt": (5, 2000),
    "ast": (5, 2000),
    "alt": (5, 2000),
    "uric_acid": (50, 900),
    "endometrium_mm": (1, 30),
    # Huyết học
    "rbc": (2.0, 8.0),
    "hgb": (70, 200),
    "hct": (0.2, 0.65),
    "plt": (50, 800),
    "wbc": (1.0, 30.0),
    "mcv": (50, 120),
    "mch": (15, 50),
    "mchc": (200, 450),
    "neutrophil_pct": (10, 90),
    "lymphocyte_pct": (5, 80),
    "mono_group_pct": (1, 40),
}


@dataclass(frozen=True)
class RowMetric:
    key: str
    label: str
    unit: str
    aliases: tuple[str, ...]


ROW_METRICS: tuple[RowMetric, ...] = (
    RowMetric("glucose", "Glucose", "mmol/L", ("glucose", "đường huyết", "duong huyet")),
    RowMetric("urea", "Urê", "mmol/L", ("urê", "ure", "ur e")),
    RowMetric("creatinine", "Creatinin", "µmol/L", ("creatinin", "creatinine", "creratinin")),
    RowMetric("cholesterol", "Cholesterol", "mmol/L", ("cholesterol",)),
    RowMetric("triglycerid", "Triglycerid", "mmol/L", ("triglycerid", "triglyceride", "trigly")),
    RowMetric("hdl", "HDL-cho", "mmol/L", ("hdl-cho", "hdl cho", "hdl")),
    RowMetric("ldl", "LDL-cho", "mmol/L", ("ldl-cho", "ldl cho", "ldl")),
    RowMetric("ggt", "GGT", "U/L", ("ggt",)),
    RowMetric("ast", "AST (GOT)", "U/L", ("ast (got)", "ast", "got")),
    RowMetric("alt", "ALT (GPT)", "U/L", ("alt (gpt)", "alt", "gpt")),
    RowMetric("uric_acid", "Acid Uric", "µmol/L", ("acid uric", "uric acid", "aciduric")),
    RowMetric("amh", "AMH", "ng/mL", ("amh",)),
    RowMetric("fsh", "FSH", "mIU/mL", ("fsh",)),
    RowMetric("lh", "LH", "mIU/mL", ("lh",)),
    RowMetric("e2", "Estradiol (E2)", "pg/mL", ("estradiol", "e2")),
    # Huyết học / CBC — aliases include OCR-garbled forms (no diacritics)
    RowMetric("rbc", "Số lượng HC", "T/L", ("so luong hc", "số lượng hc", "hong cau", "hồng cầu", "rbc", "luong hc", "hc:")),
    RowMetric("hgb", "Huyết sắc tố", "g/L", ("huyet sac to", "huyết sắc tố", "huyết sắc tô", "hemoglobin", "hgb")),
    RowMetric("hct", "Hematocrit", "L/L", ("hematocrit", "hematocnt", "hematocnit", "hct")),
    RowMetric("plt", "Tiểu cầu", "G/L", ("tieu cau", "tiểu cầu", "platelet", "plt", "luong tieu cau")),
    RowMetric("wbc", "Số lượng BC", "G/L", ("so luong bc", "số lượng bc", "luongbc", "bach cau", "bạch cầu", "wbc")),
    RowMetric("mcv", "MCV", "fL", ("mcv",)),
    RowMetric("mch", "MCH", "pg", ("mch",)),
    RowMetric("mchc", "MCHC", "g/L", ("mchc",)),
    RowMetric(
        "neutrophil_pct",
        "Đoạn trung tính",
        "%",
        ("doan trung tinh", "đoạn trung tính", "neutrophil", "trung tinh"),
    ),
    RowMetric("lymphocyte_pct", "Lympho", "%", ("lympho", "lymphocyte")),
    RowMetric(
        "mono_group_pct",
        "Mono / ưa acid-bazơ",
        "%",
        ("doan ua a", "đoạn ưa a", "ua ba zo", "ưa ba zơ", "mono"),
    ),
)


NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
RANGE_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*[-–—~]\s*\d+(?:[.,]\d+)?|[<>≤≥]=?\s*\d+(?:[.,]\d+)?"
)


def recover_decimal(key: str, value: float) -> tuple[float, bool]:
    """Fix OCR dropping decimal separators (4.87 → 487)."""
    lo, hi = TYPICAL_RANGE.get(key, (None, None))  # type: ignore[assignment]
    if lo is None:
        return value, False
    if lo <= value <= hi * 1.5:
        return value, False
    for div in (100.0, 10.0):
        candidate = value / div
        if lo <= candidate <= hi * 1.5:
            return round(candidate, 4), True
    return value, False


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("‑", "-").replace("–", "-")).strip()


def cluster_rows(boxes: list[WordBox], y_tol: int = 12) -> list[list[WordBox]]:
    if not boxes:
        return []
    ordered = sorted(boxes, key=lambda b: (b.top, b.left))
    rows: list[list[WordBox]] = []
    cur: list[WordBox] = [ordered[0]]
    cur_y = ordered[0].top
    for b in ordered[1:]:
        if abs(b.top - cur_y) <= y_tol:
            cur.append(b)
        else:
            rows.append(sorted(cur, key=lambda x: x.left))
            cur = [b]
            cur_y = b.top
    rows.append(sorted(cur, key=lambda x: x.left))
    return rows


def merge_row_text(row: list[WordBox]) -> str:
    """Join tokens; glue digit + '.' + digit back into decimals."""
    parts: list[str] = []
    i = 0
    texts = [b.text for b in row]
    while i < len(texts):
        t = texts[i]
        if (
            i + 2 < len(texts)
            and re.fullmatch(r"\d+", texts[i] or "")
            and texts[i + 1] in {".", ","}
            and re.fullmatch(r"\d+", texts[i + 2] or "")
        ):
            parts.append(f"{texts[i]}.{texts[i + 2]}")
            i += 3
            continue
        parts.append(t)
        i += 1
    return " ".join(parts)


def _match_metric(line: str) -> RowMetric | None:
    norm = _normalize(line)
    # longest alias first
    best: RowMetric | None = None
    best_len = 0
    for m in ROW_METRICS:
        for alias in m.aliases:
            if alias in norm and len(alias) > best_len:
                # require alias near start of line (name column)
                pos = norm.find(alias)
                if pos <= 24:
                    best = m
                    best_len = len(alias)
    return best


def _result_number(line: str) -> float | None:
    """Pick patient result: first number not belonging only to a reference-range pair."""
    # Drop parenthetical reference ranges first: "HC (3,9-5,4) 3.87" → "HC  3.87"
    work = re.sub(r"\([^)]*\)", " ", line)
    work = re.sub(r"\s+", " ", work).strip()

    m_comment = re.search(r"(tăng|tang|giảm|giam|high|low)", work, re.I)
    head = work[: m_comment.start()] if m_comment else work

    range_m = RANGE_RE.search(work)
    search_region = work[: range_m.start()] if range_m else head

    nums = list(NUM_RE.finditer(search_region))
    if not nums:
        nums = list(NUM_RE.finditer(work))
        if not nums:
            return None
        if range_m and nums[0].start() >= range_m.start():
            return None
    raw = nums[0].group(0).replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def extract_from_rows(
    word_boxes: list[WordBox],
    ocr_text: str = "",
    document_type: str = "lab",
) -> list[ExtractedParameter]:
    """Table-aware extract: cluster OCR boxes into rows, map metric → result cell."""
    if document_type == "prescription":
        return []

    found: dict[str, ExtractedParameter] = {}
    rows = cluster_rows(word_boxes)
    lines = [merge_row_text(r) for r in rows]
    if ocr_text:
        # also scan plain OCR lines (backup)
        lines.extend([ln.strip() for ln in ocr_text.splitlines() if ln.strip()])

    for line in lines:
        metric = _match_metric(line)
        if not metric:
            continue
        if document_type == "ultrasound" and metric.key not in {"endometrium_mm"}:
            continue
        value = _result_number(line)
        if value is None:
            # record key as missing for caller awareness? skip
            continue
        value, fixed = recover_decimal(metric.key, value)
        conf = 0.72 if fixed else 0.86
        # Don't overwrite a higher-confidence existing value with worse one
        prev = found.get(metric.key)
        if prev and (prev.confidence or 0) >= conf and prev.value is not None:
            continue
        found[metric.key] = ExtractedParameter(
            key=metric.key,
            label=metric.label,
            value=value,
            unit=metric.unit,
            raw_text=line[:160],
            confidence=conf,
            needs_human_verify=fixed or conf < 0.7,
            page=0,
            bbox=None,
        )
    return list(found.values())


def merge_extracts(*groups: list[ExtractedParameter]) -> list[ExtractedParameter]:
    """Prefer higher confidence / non-null values."""
    best: dict[str, ExtractedParameter] = {}
    for group in groups:
        for p in group:
            cur = best.get(p.key)
            if cur is None:
                best[p.key] = p
                continue
            score = (1 if p.value is not None else 0, p.confidence or 0)
            cur_score = (1 if cur.value is not None else 0, cur.confidence or 0)
            if score > cur_score:
                best[p.key] = p
    return list(best.values())
