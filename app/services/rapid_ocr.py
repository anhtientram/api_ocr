"""RapidOCR engine — ONNX port of PaddleOCR models (offline, no API key).

Better than Tesseract on scanned lab/ultrasound forms: keeps result digits
as separate boxes so lexicon / column extract can pair them.
"""

from __future__ import annotations

import io
import logging
from functools import lru_cache
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from app.services.bbox import WordBox
from app.services.table_extract import cluster_rows, merge_row_text

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_engine() -> Any:
    from rapidocr_onnxruntime import RapidOCR

    # Default ch/en models still read Latin digits well (lab metrics).
    return RapidOCR()


def available() -> bool:
    try:
        _get_engine()
        return True
    except Exception as e:
        logger.warning("RapidOCR unavailable: %s", e)
        return False


def _pil_to_bgr(img: Image.Image) -> np.ndarray:
    rgb = ImageOps.exif_transpose(img)
    if rgb.mode != "RGB":
        rgb = rgb.convert("RGB")
    # Upscale small scans for thin decimals
    w, h = rgb.size
    min_side = min(w, h)
    if min_side < 1200:
        scale = 1200 / min_side
        rgb = rgb.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    arr = np.array(rgb)
    # RapidOCR / OpenCV expect BGR
    return arr[:, :, ::-1].copy()


def _box_to_xywh(box: list) -> tuple[int, int, int, int]:
    xs = [float(p[0]) for p in box]
    ys = [float(p[1]) for p in box]
    left, top = int(min(xs)), int(min(ys))
    right, bottom = int(max(xs)), int(max(ys))
    return left, top, max(1, right - left), max(1, bottom - top)


def run_on_pil(img: Image.Image, page: int = 0) -> tuple[str, float, list[WordBox]]:
    """Return (text, avg_confidence, word_boxes)."""
    engine = _get_engine()
    bgr = _pil_to_bgr(img)
    page_h, page_w = int(bgr.shape[0]), int(bgr.shape[1])
    result, _elapse = engine(bgr)
    if not result:
        return "", 0.0, []

    word_boxes: list[WordBox] = []
    confs: list[float] = []
    for item in result:
        # item: [box(4 points), text, score]
        if not item or len(item) < 3:
            continue
        box, text, score = item[0], (item[1] or "").strip(), float(item[2] or 0.0)
        if not text:
            continue
        left, top, width, height = _box_to_xywh(box)
        confs.append(score)
        word_boxes.append(
            WordBox(
                text=text,
                conf=score,
                page=page,
                left=left,
                top=top,
                width=width,
                height=height,
                page_width=page_w,
                page_height=page_h,
            )
        )

    rows = cluster_rows(word_boxes, y_tol=16)
    text = "\n".join(merge_row_text(r) for r in rows if r)
    avg = sum(confs) / len(confs) if confs else 0.0
    return text, avg, word_boxes


def run_on_bytes(content: bytes, page: int = 0) -> tuple[str, float, list[WordBox]]:
    img = Image.open(io.BytesIO(content))
    return run_on_pil(img, page=page)
