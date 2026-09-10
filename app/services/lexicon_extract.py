"""Lexicon-first free extract — duyệt bảng chỉ số đã biết (kiểu ABC), tìm nhãn, lấy số gần nhất.

Ý tưởng đơn giản hơn crop layout:
1. Có dictionary cố định các chỉ số (glucose, rbc, hgb, …) + alias OCR.
2. Với từng chỉ số: tìm chữ/nhãn trong OCR (đã bỏ dấu, cho phép lệch 1–2 ký tự).
3. Lấy số kết quả gần nhất bên phải / cùng hàng, bỏ khoảng tham chiếu trong ngoặc.
"""

from __future__ import annotations

import re
import unicodedata

from app.models.schemas import ExtractedParameter
from app.services.bbox import WordBox
from app.services.table_extract import ROW_METRICS, TYPICAL_RANGE, recover_decimal, parse_number_token, NUM_RE as TE_NUM_RE

NUM_RE = TE_NUM_RE
PAREN_RE = re.compile(r"\([^)]*\)")
RANGE_RE = re.compile(
    r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?\s*[-–—~]\s*\d+(?:[.,]\d+)?"
)


def _fold(s: str) -> str:
    s = (s or "").lower().replace("đ", "d").replace("Đ", "d")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _compact(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _fold(s))


def _lev(a: str, b: str) -> int:
    """Tiny Levenshtein for short OCR typos (hematocnt ≈ hematocrit)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if abs(len(a) - len(b)) > 3:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _alias_hit(alias: str, haystack: str) -> bool:
    """Match alias in text: exact fold, compact, or fuzzy for longer tokens.

    Short aliases (≤3 chars like alt/lh/gpt) must be whole tokens — otherwise
    ``alt`` falsely matches inside ``Total T`` → compact ``totalt``.
    """
    a = _fold(alias).strip()
    h = _fold(haystack)
    if not a or len(a) < 2:
        return False

    # Word-boundary / token match (handles "Total T", "(ALT)", "ALT (GPT)")
    if re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", h):
        return True

    ac, hc = _compact(alias), _compact(haystack)
    if not ac:
        return False

    # Short compact forms: only exact token equality, never substring
    if len(ac) <= 3:
        tokens = re.findall(r"[a-z0-9]+", hc)
        return ac in tokens

    if ac in hc:
        # Avoid Free T 425 → compact "...freet425..." matching alias "freet4"
        start = 0
        while True:
            idx = hc.find(ac, start)
            if idx < 0:
                break
            after = hc[idx + len(ac) : idx + len(ac) + 1]
            before = hc[idx - 1] if idx > 0 else ""
            if not before.isdigit() and not after.isdigit():
                return True
            start = idx + 1

    # Fuzzy: longer alpha aliases only (avoid Free T ≈ FT4)
    if len(ac) >= 5 and not re.search(r"\d", ac):
        for w in re.findall(r"[a-z]{4,}", hc):
            if abs(len(ac) - len(w)) > 1:
                continue
            if _lev(ac, w) <= 2:
                return True
    return False
def _plausible(key: str, value: float) -> bool:
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


def _numbers_from_segment(segment: str) -> list[float]:
    """Numbers outside parentheses / not pure reference ranges."""
    # Drop paren blocks even if OCR lost the closing ')'
    cleaned = re.sub(r"\([^)]*\)?", " ", segment)
    cleaned = re.sub(r"\b(nam|nu|nữ)\b\s*[:\-]?\s*", " ", cleaned, flags=re.I)
    cleaned = RANGE_RE.sub(" ", cleaned)
    out: list[float] = []
    for m in NUM_RE.finditer(cleaned):
        val = parse_number_token(m.group(0))
        if val is not None:
            out.append(val)
    return out

def _slash_pair(segment: str) -> tuple[float, float] | None:
    """Parse A/B pairs like 145/90 or 4.35/139."""
    m = re.search(
        r"(?<![A-Za-z0-9])(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)(?![A-Za-z])",
        segment,
    )
    if not m:
        return None
    a = parse_number_token(m.group(1))
    b = parse_number_token(m.group(2))
    if a is None or b is None:
        return None
    return a, b


def _scan_text_for_metric(ocr_text: str, key: str, aliases: tuple[str, ...]) -> float | None:
    """Find alias in plain OCR text, take first plausible number after it on same line / nearby."""
    if not ocr_text:
        return None
    lines = ocr_text.splitlines()

    # Global BP pattern (value often separated from "Huyết áp" label by OCR wrap)
    if key in {"bp_systolic", "bp_diastolic"}:
        for line in lines:
            pair = _slash_pair(line)
            if not pair:
                continue
            folded = _fold(line)
            if "mmhg" in folded or "huyet ap" in folded or _alias_hit("huyet ap", line):
                left, right = pair
                pick = left if key == "bp_systolic" else right
                fixed, _ = recover_decimal(key, pick)
                if _plausible(key, fixed):
                    return fixed

    for i, line in enumerate(lines):
        if not any(_alias_hit(a, line) for a in aliases):
            continue
        # Prefer text AFTER the alias occurrence
        folded = _fold(line)
        after = line
        for a in sorted(aliases, key=len, reverse=True):
            pos = folded.find(_fold(a))
            if pos >= 0:
                after = line[pos + len(a) :]
                break

        # Blood pressure / electrolyte slash pairs
        if key in {"bp_systolic", "bp_diastolic", "potassium", "sodium"}:
            pair = _slash_pair(after) or _slash_pair(line)
            if not pair and i + 1 < len(lines):
                pair = _slash_pair(lines[i + 1])
            if not pair and i > 0:
                pair = _slash_pair(lines[i - 1])
            if pair:
                left, right = pair
                pick = left if key in {"bp_systolic", "potassium"} else right
                fixed, _ = recover_decimal(key, pick)
                if _plausible(key, fixed):
                    return fixed

        candidates = _numbers_from_segment(after) or _numbers_from_segment(line)
        # Also peek next line (result sometimes below)
        if i + 1 < len(lines):
            candidates = candidates + _numbers_from_segment(lines[i + 1])
        for cand in candidates:
            fixed, _ = recover_decimal(key, cand)
            if _plausible(key, fixed):
                return fixed
    return None


def _cluster_rows(boxes: list[WordBox], y_tol: int = 14) -> list[list[WordBox]]:
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


def _scan_boxes_for_metric(boxes: list[WordBox], key: str, aliases: tuple[str, ...]) -> float | None:
    """Geometry: find label on a row, take result number in the same half-column."""
    if not boxes:
        return None
    page_mid = max(b.left + b.width for b in boxes) / 2.0
    rows = _cluster_rows(boxes)
    for row in rows:
        texts = [b.text for b in row]
        joined = " ".join(texts)
        if not any(_alias_hit(a, joined) for a in aliases):
            continue

        label_right = 0
        label_cx = 0
        for idx, b in enumerate(row):
            token = b.text
            hit = any(_alias_hit(a, token) for a in aliases)
            if not hit:
                for width in (2, 3, 4):
                    if idx + width > len(row):
                        break
                    window = " ".join(texts[idx : idx + width])
                    if any(_alias_hit(a, window) for a in aliases):
                        end_b = row[idx + width - 1]
                        label_right = max(label_right, end_b.left + end_b.width)
                        label_cx = (b.left + end_b.left + end_b.width) / 2
                        hit = True
                        break
            if hit and label_right == 0:
                label_right = b.left + b.width
                label_cx = b.left + b.width / 2

        if label_right <= 0:
            continue

        same_half = [
            b
            for b in row
            if b.left >= label_right - 5
            and (
                (label_cx < page_mid and (b.left + b.width / 2) < page_mid)
                or (label_cx >= page_mid and (b.left + b.width / 2) >= page_mid)
            )
        ]
        right_nums: list[tuple[int, float]] = []
        for b in same_half:
            m = NUM_RE.search(b.text)
            if not m:
                continue
            val = parse_number_token(m.group(0))
            if val is None:
                continue
            # Skip tiny gaps (often reference fragment glued to label)
            if b.left - label_right < 40 and val < 20 and key not in {"hct", "hdl", "ldl", "rbc"}:
                # still allow; filter via plausible later
                pass
            right_nums.append((b.left, val))

        # Prefer rightmost number in the half (Kết quả column sits right of Chỉ số)
        right_nums.sort(key=lambda x: x[0], reverse=True)
        for _, cand in right_nums:
            fixed, _ = recover_decimal(key, cand)
            if _plausible(key, fixed):
                return fixed
    return None


def lexicon_extract(
    ocr_text: str,
    word_boxes: list[WordBox] | None = None,
    document_type: str = "lab",
) -> list[ExtractedParameter]:
    """Walk the known metric alphabet one-by-one (0 token)."""
    if document_type == "prescription":
        return []
    boxes = word_boxes or []
    found: dict[str, ExtractedParameter] = {}

    for metric in ROW_METRICS:
        if document_type == "ultrasound" and metric.key not in {
            "endometrium_mm",
            "ef_pct",
            "lvdd_mm",
            "lvds_mm",
            "ivsd_mm",
            "la_mm",
            "paps_mmhg",
        }:
            continue

        value: float | None = None
        source = ""

        # 1) Geometry on word boxes (preferred when available)
        if boxes:
            value = _scan_boxes_for_metric(boxes, metric.key, metric.aliases)
            if value is not None:
                source = "lexicon:boxes"

        # 2) Plain OCR text dictionary scan
        if value is None:
            value = _scan_text_for_metric(ocr_text, metric.key, metric.aliases)
            if value is not None:
                source = "lexicon:text"

        if value is None:
            continue

        value, fixed = recover_decimal(metric.key, value)
        if not _plausible(metric.key, value):
            continue

        conf = 0.7 if fixed else 0.82
        found[metric.key] = ExtractedParameter(
            key=metric.key,
            label=metric.label,
            value=value,
            unit=metric.unit,
            raw_text=f"{source}:{metric.key}={value}",
            confidence=conf,
            needs_human_verify=fixed,
            page=0,
            bbox=None,
        )

    return list(found.values())
