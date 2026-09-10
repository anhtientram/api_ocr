from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.models.schemas import BBox, ExtractedParameter, NormalizedBBox, PageGeometry


@dataclass
class WordBox:
    text: str
    conf: float
    page: int
    left: int
    top: int
    width: int
    height: int
    page_width: int = 0
    page_height: int = 0


def to_normalized(bbox: BBox, page_width: int, page_height: int) -> Optional[NormalizedBBox]:
    if page_width <= 0 or page_height <= 0:
        return None
    return NormalizedBBox(
        x_pct=round(100.0 * bbox.x / page_width, 4),
        y_pct=round(100.0 * bbox.y / page_height, 4),
        w_pct=round(100.0 * bbox.w / page_width, 4),
        h_pct=round(100.0 * bbox.h / page_height, 4),
    )


def attach_bboxes(
    params: list[ExtractedParameter],
    word_boxes: list[WordBox],
) -> tuple[list[ExtractedParameter], dict, list[PageGeometry]]:
    """Fuzzy-match parameter raw_text / key against OCR word boxes.

    Returns absolute + normalized (%) boxes; coordinate_space is always derivative.
    """
    source_trace: dict = {}
    updated: list[ExtractedParameter] = []
    geometry_by_page: dict[int, PageGeometry] = {}

    for b in word_boxes:
        if b.page_width > 0 and b.page_height > 0 and b.page not in geometry_by_page:
            geometry_by_page[b.page] = PageGeometry(
                page=b.page,
                width=b.page_width,
                height=b.page_height,
                coordinate_space="derivative",
            )

    for p in params:
        needle = (p.raw_text or p.label or p.key or "").strip()
        box = _best_box(needle, p.key, word_boxes)
        data = p.model_dump()
        if box:
            bbox = BBox(x=box.left, y=box.top, w=box.width, h=box.height)
            data["bbox"] = bbox
            data["page"] = box.page
            pw = box.page_width or (geometry_by_page.get(box.page).width if box.page in geometry_by_page else 0)
            ph = box.page_height or (geometry_by_page.get(box.page).height if box.page in geometry_by_page else 0)
            bbox_norm = to_normalized(bbox, pw, ph)
            data["bbox_norm"] = bbox_norm
            trace: dict = {
                "page": box.page,
                "bbox": bbox.model_dump(),
                "coordinate_space": "derivative",
            }
            if bbox_norm:
                trace["bbox_norm"] = bbox_norm.model_dump()
            if pw and ph:
                trace["page_width"] = pw
                trace["page_height"] = ph
            source_trace[p.key] = trace
        else:
            data["bbox"] = None
            data["bbox_norm"] = None
        updated.append(ExtractedParameter(**data))

    return updated, source_trace, list(geometry_by_page.values())


def _best_box(needle: str, key: str, boxes: list[WordBox]) -> WordBox | None:
    if not boxes:
        return None
    tokens = [t for t in re.split(r"\s+", needle) if t]
    key_l = key.lower()
    label_tokens = [key_l, key_l.upper(), key.replace("_", " ")]

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
