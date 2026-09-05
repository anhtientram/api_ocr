"""Layout-aware free extract: crop label/result columns, pair by vertical order.

Handles Vietnamese dual-column lab forms (Chỉ số|Kết quả|Chỉ số|Kết quả)
where full-page Tesseract mixes columns and drops result digits.
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass

from PIL import Image, ImageEnhance, ImageOps

from app.models.schemas import ExtractedParameter
from app.services.table_extract import ROW_METRICS, RowMetric, recover_decimal

NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")
PAREN_RE = re.compile(r"\([^)]*\)")
FOOTER_RE = re.compile(
    r"(hướng\s*dẫn|huong\s*dan|trưởng\s*khoa|truong\s*khoa|bác\s*sĩ|bac\s*si|"
    r"giờ\s*\d|gio\s*\d|ngày\s*\d|ngay\s*\d|20\d{2}|đồng\s*máu|dong\s*mau|"
    r"nhóm\s*máu|nhom\s*mau|thoi\s*gian\s*mau|thời\s*gian\s*máu)",
    re.I,
)


def _fold(s: str) -> str:
    s = s.lower().replace("đ", "d").replace("Đ", "d")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalize(s: str) -> str:
    s = PAREN_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s.replace("‑", "-").replace("–", "-")).strip()
    return _fold(s)


def _prep(img: Image.Image, scale: float = 3.0) -> Image.Image:
    gray = ImageOps.grayscale(img.convert("RGB"))
    gray = ImageOps.autocontrast(gray)
    gray = ImageEnhance.Contrast(gray).enhance(1.65)
    if scale != 1.0:
        gray = gray.resize(
            (max(1, int(gray.width * scale)), max(1, int(gray.height * scale))),
            Image.Resampling.LANCZOS,
        )
    return gray


def _ocr_lines(img: Image.Image, lang: str, psm: int = 6, digits_only: bool = False) -> list[str]:
    try:
        import pytesseract
    except ImportError:
        return []
    config = f"--oem 3 --psm {psm} -c preserve_interword_spaces=1"
    use_lang = lang
    if digits_only:
        config += " -c tessedit_char_whitelist=0123456789.,"
        use_lang = "eng"
    try:
        text = pytesseract.image_to_string(img, lang=use_lang, config=config) or ""
    except Exception:
        return []
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _match_metrics_in_order(lines: list[str]) -> list[tuple[RowMetric, str]]:
    found: list[tuple[RowMetric, str]] = []
    seen: set[str] = set()
    ranked = sorted(
        ((m, _fold(a)) for m in ROW_METRICS for a in m.aliases),
        key=lambda t: len(t[1]),
        reverse=True,
    )
    for line in lines:
        if FOOTER_RE.search(line):
            break
        norm = _normalize(line)
        compact = norm.replace(" ", "")
        best: RowMetric | None = None
        best_len = 0
        for metric, alias in ranked:
            if metric.key in seen:
                continue
            alias_c = alias.replace(" ", "")
            hit = alias in norm or alias_c in compact
            if not hit and metric.key == "hct" and "hematoc" in compact:
                hit = True
                alias = "hematoc"
            if hit and len(alias) > best_len:
                best = metric
                best_len = len(alias)
        if best:
            seen.add(best.key)
            found.append((best, line))
    return found


def _parse_result_numbers(lines: list[str]) -> list[float]:
    values: list[float] = []
    for line in lines:
        if FOOTER_RE.search(line):
            break
        cleaned = PAREN_RE.sub(" ", line)
        m = NUM_RE.search(cleaned)
        if not m:
            continue
        raw = m.group(0).replace(",", ".")
        try:
            val = float(raw)
        except ValueError:
            continue
        if val >= 1900 and val <= 2100 and "." not in raw:
            continue
        values.append(val)
    return values


def _in_plausible_range(key: str, value: float) -> bool:
    lo_hi = {
        "rbc": (2.0, 8.0),
        "hgb": (70, 220),
        "hct": (0.2, 0.7),
        "plt": (50, 800),
        "wbc": (1.0, 40.0),
        "mcv": (60, 120),
        "mch": (15, 50),
        "mchc": (250, 450),
        "neutrophil_pct": (10, 90),
        "lymphocyte_pct": (5, 80),
        "mono_group_pct": (1, 40),
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
    }.get(key)
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


def _pair_side(
    label_lines: list[str],
    result_lines: list[str],
) -> list[ExtractedParameter]:
    metrics = _match_metrics_in_order(label_lines)
    numbers = _parse_result_numbers(result_lines)
    if not metrics or not numbers:
        return []

    out: list[ExtractedParameter] = []
    ni = 0
    for metric, label_line in metrics:
        matched_val: float | None = None
        matched_fixed = False
        probe = ni
        while probe < len(numbers):
            cand = numbers[probe]
            cand_fixed, fixed = recover_decimal(metric.key, cand)
            if _in_plausible_range(metric.key, cand_fixed):
                matched_val = cand_fixed
                matched_fixed = fixed
                ni = probe + 1
                break
            probe += 1
        if matched_val is None:
            continue
        conf = 0.74 if matched_fixed else 0.88
        out.append(
            ExtractedParameter(
                key=metric.key,
                label=metric.label,
                value=matched_val,
                unit=metric.unit,
                raw_text=f"{label_line[:80]} → {matched_val}",
                confidence=conf,
                needs_human_verify=matched_fixed or conf < 0.7,
                page=0,
                bbox=None,
            )
        )
    return out


def _best_ocr_lines(
    img: Image.Image,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    lang: str,
    prefer_numbers: bool = False,
) -> list[str]:
    """Try a few crop variants; keep the richest parse (capped for latency)."""
    w, h = img.size
    variants = [
        (x0, x1, y0, y1, 3.0, 6),
        (x0 - 0.02, x1 + 0.02, y0, y1 + 0.02, 3.0, 6),
        (x0 + 0.01, x1 - 0.01, y0 + 0.02, y1 - 0.02, 2.5, 4),
    ]
    candidates: list[list[str]] = []
    for xa, xb, ya, yb, scale, psm in variants:
        xa, xb = max(0.0, xa), min(1.0, xb)
        ya, yb = max(0.0, ya), min(1.0, yb)
        if xb - xa < 0.08 or yb - ya < 0.1:
            continue
        crop = img.crop((int(w * xa), int(h * ya), int(w * xb), int(h * yb)))
        # Prefer normal OCR first; digits-only as fallback enricher
        lines = _ocr_lines(_prep(crop, scale=scale), lang=lang, psm=psm, digits_only=False)
        if prefer_numbers and len(_parse_result_numbers(lines)) < 2:
            digit_lines = _ocr_lines(_prep(crop, scale=scale), lang="eng", psm=psm, digits_only=True)
            if len(_parse_result_numbers(digit_lines)) > len(_parse_result_numbers(lines)):
                lines = digit_lines
        if not lines:
            continue
        candidates.append(lines)
        if prefer_numbers and len(_parse_result_numbers(lines)) >= 4:
            return lines
        if not prefer_numbers and len(_match_metrics_in_order(lines)) >= 3:
            return lines

    if not candidates:
        return []
    if prefer_numbers:
        return max(candidates, key=lambda ln: (len(_parse_result_numbers(ln)), len(ln)))
    return max(candidates, key=lambda ln: (len(_match_metrics_in_order(ln)), len(ln)))


def _load_image(content: bytes) -> Image.Image | None:
    try:
        return Image.open(io.BytesIO(content))
    except Exception:
        return None


def extract_from_column_layout(
    content: bytes,
    filename: str = "",
    document_type: str = "lab",
) -> list[ExtractedParameter]:
    """Free-mode dual-column (and single-column name-band) extract from image bytes."""
    if document_type not in {"lab", "other"}:
        return []
    suffix = (filename or "").lower()
    if suffix.endswith(".pdf"):
        return []

    img = _load_image(content)
    if img is None:
        return []
    img = ImageOps.exif_transpose(img)
    w, h = img.size
    if w < 80 or h < 80:
        return []

    y0, y1 = 0.20, 0.66

    ll = _best_ocr_lines(img, 0.00, 0.42, y0, y1, "vie+eng", prefer_numbers=False)
    lr = _best_ocr_lines(img, 0.34, 0.54, y0, y1, "eng", prefer_numbers=True)
    rl = _best_ocr_lines(img, 0.48, 0.86, y0, y1, "vie+eng", prefer_numbers=False)
    # Right result column is narrow; slightly tighter Y avoids footer swallowing digits
    rr = _best_ocr_lines(img, 0.80, 1.00, 0.22, 0.60, "eng", prefer_numbers=True)
    if len(_parse_result_numbers(rr)) < 3:
        rr = _best_ocr_lines(img, 0.78, 1.00, 0.20, 0.62, "eng", prefer_numbers=True)
    names = _best_ocr_lines(img, 0.00, 0.38, y0, 0.85, "vie+eng", prefer_numbers=False)
    mid = _best_ocr_lines(img, 0.30, 0.52, y0, 0.85, "eng", prefer_numbers=True)

    left = _pair_side(ll, lr)
    right = _pair_side(rl, rr)
    single = _pair_side(names, mid)

    dual = left + right
    if len(dual) >= len(single) and len(dual) >= 3:
        return dual
    if len(single) >= 3:
        return single
    by_key: dict[str, ExtractedParameter] = {}
    for p in dual + single:
        prev = by_key.get(p.key)
        if prev is None or (p.confidence or 0) > (prev.confidence or 0):
            by_key[p.key] = p
    return list(by_key.values())
