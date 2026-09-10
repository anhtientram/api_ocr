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
    "progesterone": (0.1, 50),
    "glucose": (1.5, 40),
    "hba1c": (3.0, 15.0),
    "urea": (1, 40),
    "creatinine": (20, 1500),
    "egfr": (5, 150),
    "cholesterol": (1.5, 15),
    "triglycerid": (0.2, 25),
    "hdl": (0.2, 5),
    "ldl": (0.5, 12),
    "ggt": (5, 2000),
    "ast": (5, 2000),
    "alt": (5, 2000),
    "bilirubin_tp": (1, 500),
    "albumin": (15, 60),
    "uric_acid": (50, 900),
    "endometrium_mm": (1, 30),
    # Nam học / hormone
    "total_t": (1.0, 50.0),
    "free_t": (50.0, 1500.0),
    "prolactin": (20.0, 2000.0),
    "sperm_concentration": (0.1, 300.0),
    "sperm_volume": (0.2, 10.0),
    "psa": (0.01, 100),
    # Tuyến giáp
    "tsh": (0.01, 100),
    "ft4": (0.5, 50),
    "ft3": (1.0, 20),
    # Tim mạch / biomarkers
    "nt_probnp": (5, 50000),
    "bnp": (5, 20000),
    "troponin_t": (1, 10000),
    "troponin_i": (0.001, 100),
    "ck_mb": (1, 500),
    "ck": (10, 5000),
    "bp_systolic": (70, 260),
    "bp_diastolic": (40, 160),
    "heart_rate": (30, 220),
    "ef_pct": (10, 85),
    "lvdd_mm": (20, 90),
    "lvds_mm": (10, 70),
    "ivsd_mm": (4, 30),
    "la_mm": (15, 80),
    "paps_mmhg": (10, 120),
    "potassium": (2.0, 7.5),
    "sodium": (110, 170),
    # Viêm / khác
    "crp": (0.1, 400),
    "esr": (1, 150),
    "ferritin": (5, 2000),
    "vitamin_d": (5, 150),
    "inr": (0.5, 10),
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
    # --- Sinh hóa thường quy ---
    RowMetric("glucose", "Glucose", "mmol/L", ("glucose", "đường huyết", "duong huyet")),
    RowMetric("hba1c", "HbA1c", "%", ("hba1c", "hb a1c", "a1c")),
    RowMetric("urea", "Urê", "mmol/L", ("urê", "ure", "ur e", "bun")),
    RowMetric("creatinine", "Creatinin", "µmol/L", ("creatinin", "creatinine", "creratinin")),
    RowMetric("egfr", "eGFR", "mL/min", ("egfr", "e gfr", "do loc cau than")),
    RowMetric(
        "cholesterol",
        "Cholesterol toàn phần",
        "mmol/L",
        ("cholesterol toan phan", "cholesterol toàn phần", "cholesterol"),
    ),
    RowMetric("triglycerid", "Triglycerid", "mmol/L", ("triglycerid", "triglyceride", "trigly")),
    RowMetric(
        "hdl",
        "HDL-Cholesterol",
        "mmol/L",
        ("hdl-cholesterol", "hdl cholesterol", "hdl-cho", "hdl cho", "hdl"),
    ),
    RowMetric(
        "ldl",
        "LDL-Cholesterol",
        "mmol/L",
        ("ldl-cholesterol", "ldl cholesterol", "ldl-cho", "ldl cho", "ldl"),
    ),
    RowMetric("ggt", "GGT", "U/L", ("ggt",)),
    RowMetric("ast", "AST (GOT)", "U/L", ("ast (got)", "ast", "got")),
    RowMetric("alt", "ALT (GPT)", "U/L", ("alt (gpt)", "alt", "gpt")),
    RowMetric(
        "bilirubin_tp",
        "Bilirubin TP",
        "µmol/L",
        ("bilirubin tp", "bilirubin toan phan", "bilirubin toàn phần", "bilirubin"),
    ),
    RowMetric("albumin", "Albumin", "g/L", ("albumin",)),
    RowMetric("uric_acid", "Acid Uric", "µmol/L", ("acid uric", "uric acid", "aciduric")),
    RowMetric("potassium", "Kali (K+)", "mmol/L", ("kali", "potassium", "k+", "dien giai do")),
    RowMetric("sodium", "Natri (Na+)", "mmol/L", ("natri", "sodium", "na+")),
    # --- Tim mạch ---
    RowMetric(
        "nt_probnp",
        "NT-proBNP",
        "pg/mL",
        ("nt-probnp", "nt probnp", "ntprobnp", "pro bnp", "dau an suy tim"),
    ),
    RowMetric("bnp", "BNP", "pg/mL", ("bnp",)),
    RowMetric(
        "troponin_t",
        "Troponin T (hs-cTnT)",
        "ng/L",
        ("troponin t sieu nhay", "troponin t", "hs-ctnt", "hs ctnt", "hstnt"),
    ),
    RowMetric("troponin_i", "Troponin I", "ng/mL", ("troponin i", "hs-ctni", "hstni")),
    RowMetric("ck_mb", "CK-MB", "U/L", ("ck-mb", "ck mb", "ckmb", "men co tim")),
    RowMetric("ck", "CK toàn phần", "U/L", ("ck toan phan", "creatine kinase")),
    RowMetric("bp_systolic", "Huyết áp tâm thu", "mmHg", ("huyet ap", "huyết áp", "blood pressure")),
    RowMetric("bp_diastolic", "Huyết áp tâm trương", "mmHg", ("tam truong", "diastolic")),
    RowMetric(
        "heart_rate",
        "Mạch / nhịp tim",
        "lần/phút",
        ("tan so", "tần số", "nhip xoang", "ck/p", "chu ky/phut"),
    ),
    RowMetric(
        "ef_pct",
        "EF (phân suất tống máu)",
        "%",
        ("ef(simpson", "ef simpson", "simpson biplane", "phan suat tong mau", "ejection fraction"),
    ),
    RowMetric(
        "lvdd_mm",
        "LVDd",
        "mm",
        ("lvdd", "that trai tam truong", "thất trái tâm trương", "duong kinh that trai tam truong"),
    ),
    RowMetric(
        "lvds_mm",
        "LVDs",
        "mm",
        ("lvds", "that trai tam thu", "thất trái tâm thu", "duong kinh that trai tam thu"),
    ),
    RowMetric(
        "ivsd_mm",
        "IVSd",
        "mm",
        ("ivsd", "do day vach lien that", "độ dày vách liên thất", "vach lien that"),
    ),
    RowMetric(
        "la_mm",
        "Nhĩ trái (LA)",
        "mm",
        ("kich thuoc nhi trai", "kích thước nhĩ trái", "nhi trai", "nhĩ trái"),
    ),
    RowMetric(
        "paps_mmhg",
        "PAPs",
        "mmHg",
        ("paps", "ap luc dm phoi", "áp lực đm phổi", "pa pressure"),
    ),
    # --- Nam học ---
    RowMetric(
        "total_t",
        "Testosterone toàn phần (Total T)",
        "nmol/L",
        (
            "testosterone toan phan",
            "testosterone toàn phần",
            "total testosterone",
            "total t",
            "totalt",
        ),
    ),
    RowMetric(
        "free_t",
        "Testosterone tự do (Free T)",
        "pmol/L",
        (
            "testosterone tu do",
            "testosterone tự do",
            "testosterone ty do",
            "free testosterone",
            "free t",
            "freet",
        ),
    ),
    RowMetric("prolactin", "Prolactin", "mIU/L", ("prolactin", "prl")),
    RowMetric(
        "sperm_concentration",
        "Mật độ tinh trùng",
        "triệu/mL",
        ("mat do tinh trung", "mật độ tinh trùng", "sperm concentration"),
    ),
    RowMetric(
        "sperm_volume",
        "Thể tích mẫu (Volume)",
        "mL",
        ("the tich mau", "thể tích mẫu"),
    ),
    RowMetric("psa", "PSA", "ng/mL", ("psa toan phan", "psa", "prostate specific")),
    # --- Nội tiết nữ / hiếm muộn ---
    RowMetric("amh", "AMH", "ng/mL", ("amh", "anti-mullerian", "anti mullerian")),
    RowMetric("fsh", "FSH", "mIU/mL", ("fsh",)),
    RowMetric("lh", "LH", "mIU/mL", ("lh",)),
    RowMetric("e2", "Estradiol (E2)", "pg/mL", ("estradiol", "e2")),
    RowMetric("progesterone", "Progesterone (P4)", "ng/mL", ("progesterone", "p4")),
    RowMetric(
        "endometrium_mm",
        "Niêm mạc tử cung",
        "mm",
        ("niem mac tu cung", "niêm mạc tử cung", "niem mac", "endometrium", "nmtc"),
    ),
    # --- Tuyến giáp ---
    RowMetric("tsh", "TSH", "µIU/mL", ("tsh",)),
    RowMetric("ft4", "FT4", "pmol/L", ("ft4", "free thyroxine", "thyroxine tu do")),
    RowMetric("ft3", "FT3", "pmol/L", ("ft3", "free triiodothyronine")),
    # --- Viêm / thiếu máu dự trữ ---
    RowMetric("crp", "CRP", "mg/L", ("crp", "c-reactive", "c reactive")),
    RowMetric("esr", "ESR (máu lắng)", "mm/h", ("esr", "mau lang", "máu lắng")),
    RowMetric("ferritin", "Ferritin", "ng/mL", ("ferritin",)),
    RowMetric("vitamin_d", "Vitamin D (25-OH)", "ng/mL", ("vitamin d", "25-oh", "25ohd")),
    RowMetric("inr", "INR", "", ("inr",)),
    # --- Huyết học / CBC ---
    RowMetric("rbc", "Số lượng HC", "T/L", ("so luong hc", "số lượng hc", "hong cau", "hồng cầu", "rbc", "luong hc", "hc:")),
    RowMetric("hgb", "Huyết sắc tố", "g/L", ("huyet sac to", "huyết sắc tố", "huyết sắc tô", "hemoglobin", "hgb")),
    RowMetric("hct", "Hematocrit", "L/L", ("hematocrit", "hematocnt", "hematocnit", "hct")),
    RowMetric("plt", "Tiểu cầu", "G/L", ("tieu cau", "tiểu cầu", "platelet", "plt", "luong tieu cau")),
    RowMetric("wbc", "Số lượng BC", "G/L", ("so luong bc", "số lượng bc", "luongbc", "wbc")),
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


# Prefer US thousands (1,320.0) then plain decimals (6.52 / 6,52).
# Lookbehind blocks digits inside words (d6i); trailing letters OK for 55mm / 12.5mm.
NUM_RE = re.compile(
    r"(?<![A-Za-z0-9])\d{1,3}(?:,\d{3})+(?:\.\d+)?"
    r"|(?<![A-Za-z0-9])\d+(?:[.,]\d+)?"
)
RANGE_RE = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?\s*[-–—~]\s*\d+(?:[.,]\d+)?"
    r"|[<>≤≥]=?\s*\d+(?:[.,]\d+)?"
)


def parse_number_token(raw: str) -> float | None:
    """Parse lab numbers: 1,320.0 → 1320; 6,52 → 6.52; 6.52 → 6.52."""
    s = (raw or "").strip()
    if not s:
        return None
    try:
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", s):
            return float(s.replace(",", ""))
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", s):
            return float(s.replace(".", "").replace(",", "."))
        if re.fullmatch(r"\d+,\d{1,3}", s):
            return float(s.replace(",", "."))
        return float(s.replace(",", "."))
    except ValueError:
        return None



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
    return parse_number_token(nums[0].group(0))

def _plausible_range(key: str, value: float) -> bool:
    lo_hi = TYPICAL_RANGE.get(key)
    if not lo_hi:
        return True
    lo, hi = lo_hi
    if lo <= value <= hi:
        return True
    if value > hi:
        for div in (10.0, 100.0):
            if lo <= value / div <= hi:
                return True
    return False


def extract_from_rows(
    word_boxes: list[WordBox],
    ocr_text: str = "",
    document_type: str = "lab",
) -> list[ExtractedParameter]:
    """Table-aware extract: cluster OCR boxes into rows, map metric → result cell."""
    if document_type == "prescription":
        return []

    ultrasound_keys = {
        "endometrium_mm",
        "ef_pct",
        "lvdd_mm",
        "lvds_mm",
        "ivsd_mm",
        "la_mm",
        "paps_mmhg",
    }
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
        if document_type == "ultrasound" and metric.key not in ultrasound_keys:
            continue
        value = _result_number(line)
        if value is None:
            continue
        value, fixed = recover_decimal(metric.key, value)
        if not _plausible_range(metric.key, value):
            continue
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
    """Prefer higher confidence / non-null / in-range values."""
    best: dict[str, ExtractedParameter] = {}
    for group in groups:
        for p in group:
            cur = best.get(p.key)
            if cur is None:
                best[p.key] = p
                continue
            p_ok = p.value is not None and _plausible_range(p.key, float(p.value))
            c_ok = cur.value is not None and _plausible_range(cur.key, float(cur.value))
            score = (1 if p.value is not None else 0, 1 if p_ok else 0, p.confidence or 0)
            cur_score = (1 if cur.value is not None else 0, 1 if c_ok else 0, cur.confidence or 0)
            if score > cur_score:
                best[p.key] = p
    return list(best.values())
