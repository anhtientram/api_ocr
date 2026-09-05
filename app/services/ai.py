from __future__ import annotations

import base64
import io
import json
import time
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from app.core.config import Settings
from app.core.constants import ErrorCode
from app.core.errors import AppError
from app.models.schemas import ExtractedParameter, UsageInfo
from app.services.heuristic_extract import heuristic_extract
from app.services.postfilter import apply_verify_threshold, strip_clinical_advice

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class AiService:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def available(self) -> bool:
        return bool(self.settings.ai_enabled and self.settings.resolved_ai_api_key)

    def extract_from_image(
        self,
        image_bytes: bytes,
        document_type: str,
        mime_type: str = "image/png",
        page: int = 0,
    ) -> tuple[list[ExtractedParameter], UsageInfo, list[str], str | None, int]:
        """Vision extract. Returns params, usage, warnings, optional raw_text, elapsed_ms."""
        started = time.perf_counter()
        if not self.available:
            ms = int((time.perf_counter() - started) * 1000)
            return [], UsageInfo(model="heuristic"), ["vision_unavailable"], None, ms

        system = self._read_prompt("extract_vision_system.txt")
        user_text = json.dumps(
            {
                "document_type": document_type,
                "page": page,
                "instruction": "Read the attached lab form image. Extract only filled Kết quả values.",
            },
            ensure_ascii=False,
        )
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{b64}"
        content, usage = self._chat_multimodal(system, user_text, data_url, json_mode=True)
        parsed = self._parse_json_object(content)
        params = self._params_from_parsed(parsed)
        params = apply_verify_threshold(params, self.settings.confidence_verify_threshold)
        warnings = [str(w) for w in (parsed.get("warnings") or []) if w]
        form_status = parsed.get("form_status")
        if form_status:
            warnings.append(f"form_status:{form_status}")
        raw_text = parsed.get("raw_text")
        if isinstance(raw_text, str) and raw_text.strip():
            vision_text = raw_text.strip()
        else:
            vision_text = None
        ms = int((time.perf_counter() - started) * 1000)
        return params, usage, warnings, vision_text, ms

    def extract_parameters(self, ocr_text: str, document_type: str) -> tuple[list[ExtractedParameter], UsageInfo, int]:
        started = time.perf_counter()
        if self.available:
            try:
                params, usage = self._llm_extract(ocr_text, document_type)
                params = apply_verify_threshold(params, self.settings.confidence_verify_threshold)
                ms = int((time.perf_counter() - started) * 1000)
                return params, usage, ms
            except AppError:
                raise
            except Exception as e:
                raise AppError(ErrorCode.AI_FAILED, "AI extraction failed.", status_code=502) from e

        params = apply_verify_threshold(
            heuristic_extract(ocr_text, document_type),
            self.settings.confidence_verify_threshold,
        )
        ms = int((time.perf_counter() - started) * 1000)
        return params, UsageInfo(model="heuristic", prompt_tokens=0, completion_tokens=0), ms

    def summarize(
        self,
        layer1: dict[str, Any],
        layer2: dict[str, Any],
        params: list[ExtractedParameter],
        document_hints: list[str],
        *,
        use_ai: bool = True,
    ) -> tuple[str, UsageInfo]:
        payload = {
            "layer1_clinical_notes": layer1,
            "layer2_clinical_data": layer2,
            "extracted_parameters": [p.model_dump() for p in params],
            "document_hints": document_hints,
        }
        if use_ai and self.available:
            try:
                text, usage = self._llm_summary(payload)
                return strip_clinical_advice(text), usage
            except AppError:
                raise
            except Exception as e:
                raise AppError(ErrorCode.AI_FAILED, "AI summary failed.", status_code=502) from e

        bits: list[str] = []
        if params:
            filled = [p for p in params if p.value is not None]
            if filled:
                bits.append(
                    "Chỉ số đã trích: "
                    + ", ".join(
                        f"{p.label}={p.value}{' ' + p.unit if p.unit else ''}".strip() for p in filled
                    )
                    + "."
                )
            else:
                bits.append("Không có chỉ số kết quả đã điền trên phiếu.")
        hist = (layer1 or {}).get("medical_history")
        if hist:
            bits.append(f"Tiền sử (đã anonymize): {hist}.")
        allergies = (layer1 or {}).get("allergies")
        if allergies:
            bits.append(f"Dị ứng: {allergies}.")
        meds = (layer1 or {}).get("current_medications")
        if meds:
            bits.append(f"Thuốc đang dùng (khách khai): {meds}.")
        if not bits:
            bits.append("Chưa có đủ dữ liệu để tóm tắt.")
        text = strip_clinical_advice(" ".join(bits))
        return text, UsageInfo(model="heuristic", prompt_tokens=0, completion_tokens=0)

    def _read_prompt(self, name: str) -> str:
        return (PROMPTS_DIR / name).read_text(encoding="utf-8").strip()

    def _chat(self, system: str, user: str, *, json_mode: bool = False) -> tuple[str, UsageInfo]:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self._chat_messages(messages, json_mode=json_mode)

    def _chat_multimodal(
        self,
        system: str,
        user_text: str,
        image_data_url: str,
        *,
        json_mode: bool = False,
    ) -> tuple[str, UsageInfo]:
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ]
        return self._chat_messages(messages, json_mode=json_mode)

    def _chat_messages(self, messages: list[dict[str, Any]], *, json_mode: bool = False) -> tuple[str, UsageInfo]:
        api_key = self.settings.resolved_ai_api_key
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.settings.ai_model,
            "temperature": 0,
            "messages": messages,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        url = self.settings.ai_base_url.rstrip("/") + "/chat/completions"
        try:
            with httpx.Client(timeout=self.settings.ai_timeout_seconds) as client:
                resp = client.post(url, headers=headers, json=body)
        except httpx.TimeoutException as e:
            raise AppError(ErrorCode.AI_FAILED, "AI provider timeout.", status_code=504) from e
        except httpx.HTTPError as e:
            raise AppError(ErrorCode.AI_FAILED, "AI provider unreachable.", status_code=502) from e

        if resp.status_code >= 400:
            raise AppError(ErrorCode.AI_FAILED, f"AI provider error ({resp.status_code}).", status_code=502)

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage_raw = data.get("usage") or {}
        usage = UsageInfo(
            prompt_tokens=usage_raw.get("prompt_tokens"),
            completion_tokens=usage_raw.get("completion_tokens"),
            model=self.settings.ai_model,
        )
        return content, usage

    def _llm_extract(self, ocr_text: str, document_type: str) -> tuple[list[ExtractedParameter], UsageInfo]:
        system = self._read_prompt("extract_system.txt")
        user = json.dumps({"document_type": document_type, "ocr_text": ocr_text}, ensure_ascii=False)
        content, usage = self._chat(system, user, json_mode=True)
        parsed = self._parse_json_object(content)
        return self._params_from_parsed(parsed), usage

    def _llm_summary(self, payload: dict[str, Any]) -> tuple[str, UsageInfo]:
        system = self._read_prompt("summary_system.txt")
        user = json.dumps(payload, ensure_ascii=False)
        content, usage = self._chat(system, user)
        return content.strip(), usage

    def _params_from_parsed(self, parsed: dict[str, Any]) -> list[ExtractedParameter]:
        items = parsed.get("parameters") or parsed.get("extracted_parameters") or []
        params: list[ExtractedParameter] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            params.append(
                ExtractedParameter(
                    key=key,
                    label=str(item.get("label") or key),
                    value=item.get("value"),
                    unit=item.get("unit"),
                    raw_text=item.get("raw_text"),
                    confidence=float(item.get("confidence") or 0.5),
                    needs_human_verify=bool(item.get("needs_human_verify") or False),
                    page=int(item.get("page") or 0),
                    bbox=None,
                )
            )
        return params

    def _parse_json_object(self, content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
            if isinstance(data, list):
                return {"parameters": data}
        except json.JSONDecodeError:
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict):
                return data
        raise AppError(ErrorCode.AI_FAILED, "AI returned invalid JSON.", status_code=502)


def prepare_images_for_vision(
    content: bytes,
    filename: str,
    content_type: str | None,
    max_pages: int = 3,
    dpi: int = 200,
) -> list[tuple[bytes, str, int]]:
    """Return list of (png_bytes, mime, page_index)."""
    mime = (content_type or "").split(";")[0].strip().lower()
    suffix = Path(filename or "upload").suffix.lower()
    is_pdf = mime == "application/pdf" or suffix == ".pdf"

    if is_pdf:
        try:
            from pdf2image import convert_from_bytes
        except ImportError as e:
            raise AppError(ErrorCode.OCR_FAILED, "pdf2image is not installed.", status_code=500) from e
        try:
            images = convert_from_bytes(content, dpi=dpi, fmt="png", first_page=1, last_page=max_pages)
        except Exception as e:
            raise AppError(ErrorCode.INVALID_FILE, "Unable to read PDF.", status_code=400) from e
        out: list[tuple[bytes, str, int]] = []
        for idx, img in enumerate(images):
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="PNG")
            out.append((buf.getvalue(), "image/png", idx))
        return out

    # Normalize any image to PNG for vision
    try:
        img = Image.open(io.BytesIO(content))
        img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return [(buf.getvalue(), "image/png", 0)]
    except Exception as e:
        raise AppError(ErrorCode.INVALID_FILE, "Unable to read image.", status_code=400) from e
