from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.schemas import BBox, ExtractedParameter


@dataclass
class WordBox:
    text: str
    conf: float
    page: int
    left: int
    top: int
    width: int
    height: int


def attach_bboxes(
    params: list[ExtractedParameter],
    word_boxes: list[WordBox],
) -> tuple[list[ExtractedParameter], dict]:
    """Fuzzy-match parameter raw_text / key against OCR word boxes."""
    source_trace: dict = {}
    updated: list[ExtractedParameter] = []

    for p in params:
        needle = (p.raw_text or p.label or p.key or "").strip()
        box = _best_box(needle, p.key, word_boxes)
        data = p.model_dump()
        if box:
            bbox = BBox(x=box.left, y=box.top, w=box.width, h=box.height)
            data["bbox"] = bbox
            data["page"] = box.page
            source_trace[p.key] = {"page": box.page, "bbox": bbox.model_dump()}
        else:
            data["bbox"] = None
        updated.append(ExtractedParameter(**data))

    return updated, source_trace


def _best_box(needle: str, key: str, boxes: list[WordBox]) -> WordBox | None:
    if not boxes:
        return None
    tokens = [t for t in re.split(r"\s+", needle) if t]
    key_l = key.lower()
    label_tokens = [key_l, key_l.upper(), key.replace("_", " ")]

    # Prefer line-like groups containing the metric name
    for b in boxes:
        t = b.text.strip()
        if not t:
            continue
        tl = t.lower()
        if key_l in tl or any(tok.lower() in tl for tok in label_tokens if len(tok) >= 2):
            return b
        if tokens and tokens[0].lower() in tl:
            return b
    return None
