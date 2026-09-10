from __future__ import annotations

import io
import time
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.core.config import Settings
from app.core.constants import ErrorCode
from app.core.errors import AppError
from app.services.bbox import WordBox
from app.services.table_extract import cluster_rows, merge_row_text

ALLOWED_IMAGE_MIME = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
}
ALLOWED_PDF_MIME = {"application/pdf"}


@dataclass
class PageOcrResult:
    page: int
    text: str
    confidence: float
    word_boxes: list[WordBox] = field(default_factory=list)
    engine: str = "tesseract"


@dataclass
class OcrResult:
    text: str
    confidence: float
    pages: list[PageOcrResult]
    ocr_ms: int
    engine: str = "tesseract"


class OcrService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _resolve_engine(self) -> str:
        raw = (self.settings.ocr_engine or "paddle").strip().lower()
        if raw in {"paddle", "rapid", "rapidocr"}:
            return "paddle"
        if raw in {"tesseract", "tess"}:
            return "tesseract"
        if raw == "auto":
            return "paddle"
        return raw

    def extract(self, content: bytes, filename: str, content_type: str | None, language: str | None = None) -> OcrResult:
        started = time.perf_counter()
        lang = language or self.settings.ocr_languages
        mime = (content_type or "").split(";")[0].strip().lower()
        suffix = Path(filename or "upload").suffix.lower()
        engine = self._resolve_engine()

        if mime in ALLOWED_PDF_MIME or suffix == ".pdf":
            pages = self._ocr_pdf(content, lang, engine)
        elif mime in ALLOWED_IMAGE_MIME or suffix in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
            pages = [self._ocr_image(content, lang, page=0, engine=engine)]
        elif not mime and suffix:
            if suffix == ".pdf":
                pages = self._ocr_pdf(content, lang, engine)
            else:
                pages = [self._ocr_image(content, lang, page=0, engine=engine)]
        else:
            raise AppError(ErrorCode.UNSUPPORTED_IMAGE, "Unsupported file type. Use PNG/JPEG/WEBP/PDF.", status_code=400)

        if not pages:
            raise AppError(ErrorCode.OCR_FAILED, "No pages could be OCR'd.", status_code=422)

        # If paddle failed empty and we can fall back
        if engine == "paddle" and not any(p.text.strip() for p in pages):
            pages = self._ocr_pdf(content, lang, "tesseract") if (mime in ALLOWED_PDF_MIME or suffix == ".pdf") else [
                self._ocr_image(content, lang, page=0, engine="tesseract")
            ]

        texts = [p.text.strip() for p in pages if p.text and p.text.strip()]
        joined = "\n\n".join(texts).strip()
        confs = [p.confidence for p in pages if p.confidence > 0]
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        elapsed = int((time.perf_counter() - started) * 1000)
        used = pages[0].engine if pages else engine

        if not joined:
            raise AppError(ErrorCode.OCR_FAILED, "OCR produced empty text.", status_code=422)

        return OcrResult(text=joined, confidence=round(avg_conf, 4), pages=pages, ocr_ms=elapsed, engine=used)

    def _ocr_pdf(self, content: bytes, lang: str, engine: str) -> list[PageOcrResult]:
        try:
            from pdf2image import convert_from_bytes
        except ImportError as e:
            raise AppError(ErrorCode.OCR_FAILED, "pdf2image is not installed.", status_code=500) from e

        try:
            images = convert_from_bytes(
                content,
                dpi=max(self.settings.ocr_dpi, 250),
                fmt="png",
                first_page=1,
                last_page=self.settings.max_pdf_pages,
            )
        except Exception as e:
            raise AppError(ErrorCode.INVALID_FILE, "Unable to read PDF.", status_code=400) from e

        if not images:
            raise AppError(ErrorCode.INVALID_FILE, "PDF has no pages.", status_code=400)

        return [self._ocr_pil(img, lang, page=idx, engine=engine) for idx, img in enumerate(images)]

    def _ocr_image(self, content: bytes, lang: str, page: int, engine: str) -> PageOcrResult:
        try:
            img = Image.open(io.BytesIO(content))
        except Exception as e:
            raise AppError(ErrorCode.INVALID_FILE, "Unable to read image.", status_code=400) from e
        return self._ocr_pil(img, lang, page=page, engine=engine)

    def _ocr_pil(self, img: Image.Image, lang: str, page: int, engine: str) -> PageOcrResult:
        if engine == "paddle":
            try:
                from app.services import rapid_ocr

                text, conf, boxes = rapid_ocr.run_on_pil(img, page=page)
                if text.strip():
                    return PageOcrResult(
                        page=page,
                        text=text,
                        confidence=conf,
                        word_boxes=boxes,
                        engine="paddle",
                    )
            except Exception:
                # Fall through to Tesseract
                pass
            return self._ocr_tesseract(img, lang, page)

        return self._ocr_tesseract(img, lang, page)

    def _preprocess(self, img: Image.Image) -> Image.Image:
        processed = ImageOps.exif_transpose(img)
        if processed.mode not in ("RGB", "L"):
            processed = processed.convert("RGB")
        w, h = processed.size
        scale = 1.0
        min_side = min(w, h)
        if min_side < 1400:
            scale = 1400 / min_side
        if scale > 1.01:
            processed = processed.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        gray = ImageOps.grayscale(processed)
        gray = ImageOps.autocontrast(gray)
        gray = ImageEnhance.Contrast(gray).enhance(1.35)
        gray = gray.filter(ImageFilter.SHARPEN)
        return gray

    def _ocr_tesseract(self, img: Image.Image, lang: str, page: int) -> PageOcrResult:
        try:
            import pytesseract
        except ImportError as e:
            raise AppError(ErrorCode.OCR_FAILED, "pytesseract is not installed.", status_code=500) from e

        gray = self._preprocess(img)
        config = r"--oem 3 --psm 6 -c preserve_interword_spaces=1"

        try:
            data = pytesseract.image_to_data(
                gray, lang=lang, config=config, output_type=pytesseract.Output.DICT
            )
        except pytesseract.TesseractNotFoundError as e:
            raise AppError(
                ErrorCode.OCR_FAILED,
                "Tesseract binary not found. Install tesseract-ocr and language packs.",
                status_code=500,
            ) from e
        except Exception as e:
            raise AppError(ErrorCode.OCR_FAILED, "Tesseract failed to process image.", status_code=422) from e

        page_w, page_h = gray.size
        word_boxes: list[WordBox] = []
        confs: list[float] = []
        n = len(data.get("text", []))
        for i in range(n):
            raw = (data["text"][i] or "").strip()
            if not raw:
                continue
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                conf = -1
            if conf >= 0:
                confs.append(conf / 100.0)
            word_boxes.append(
                WordBox(
                    text=raw,
                    conf=max(conf, 0) / 100.0 if conf >= 0 else 0.0,
                    page=page,
                    left=int(data["left"][i]),
                    top=int(data["top"][i]),
                    width=int(data["width"][i]),
                    height=int(data["height"][i]),
                    page_width=page_w,
                    page_height=page_h,
                )
            )

        row_lines = [merge_row_text(r) for r in cluster_rows(word_boxes, y_tol=14)]
        text = "\n".join(ln for ln in row_lines if ln.strip())
        if not text.strip():
            try:
                text = pytesseract.image_to_string(gray, lang=lang, config=config) or ""
            except Exception:
                text = ""

        avg = sum(confs) / len(confs) if confs else 0.0
        return PageOcrResult(page=page, text=text, confidence=avg, word_boxes=word_boxes, engine="tesseract")
