from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.core.config import Settings, get_settings
from app.core.constants import DocumentType, ErrorCode
from app.core.errors import AppError
from app.core.security import require_proxy_auth
from app.models.schemas import ExtractedParameter, OcrExtractResponse, SummaryRequest, SummaryResponse, UsageInfo
from app.services.ai import AiService, prepare_images_for_vision
from app.services.bbox import WordBox, attach_bboxes
from app.services.heuristic_extract import heuristic_extract
from app.services.ocr import OcrService
from app.services.pii import redact_pii
from app.services.postfilter import apply_verify_threshold, strip_clinical_advice
from app.services.column_extract import extract_from_column_layout
from app.services.lexicon_extract import lexicon_extract
from app.services.table_extract import extract_from_rows, merge_extracts

router = APIRouter(prefix="/v1", dependencies=[Depends(require_proxy_auth)])


def _parse_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _local_extract(
    ocr_text: str,
    word_boxes: list[WordBox],
    document_type: str,
    threshold: float,
    file_bytes: bytes | None = None,
    filename: str = "",
) -> list[ExtractedParameter]:
    # 1) Lexicon ABC: duyệt từng chỉ số đã biết → tìm nhãn → lấy số gần nhất
    lex_params = lexicon_extract(ocr_text, word_boxes, document_type)
    # 2) Table rows + regex heuristic
    table_params = extract_from_rows(word_boxes, ocr_text, document_type)
    heur_params = heuristic_extract(ocr_text, document_type)
    # 3) Column-band OCR (phiếu 2 cột khi full-page mất số Kết quả)
    column_params: list[ExtractedParameter] = []
    if file_bytes:
        column_params = extract_from_column_layout(file_bytes, filename, document_type)
    # Lexicon ABC first (dictionary + geometry), then rows/heuristic, then column bands.
    # First-wins-on-tie in merge_extracts — prefer precise label matches over column pairing.
    return apply_verify_threshold(
        merge_extracts(lex_params, table_params, heur_params, column_params),
        threshold,
    )

def _filled_count(params: list[ExtractedParameter]) -> int:
    return sum(1 for p in params if p.value is not None)


def _run_vision(
    ai: AiService,
    settings: Settings,
    content: bytes,
    filename: str,
    content_type: str | None,
    document_type: str,
) -> tuple[list[ExtractedParameter], UsageInfo, list[str], str | None, int]:
    images = prepare_images_for_vision(
        content,
        filename,
        content_type,
        max_pages=min(3, settings.max_pdf_pages),
        dpi=settings.ocr_dpi,
    )
    all_params: list[ExtractedParameter] = []
    vision_texts: list[str] = []
    warnings: list[str] = []
    total_prompt = 0
    total_completion = 0
    model_name = settings.ai_model
    vision_ms = 0
    for img_bytes, mime, page in images:
        p, usage, w, vtext, ms = ai.extract_from_image(
            img_bytes, document_type, mime_type=mime, page=page
        )
        for item in p:
            data = item.model_dump()
            data["page"] = page
            all_params.append(ExtractedParameter(**data))
        warnings.extend(w)
        if vtext:
            vision_texts.append(vtext)
        total_prompt += usage.prompt_tokens or 0
        total_completion += usage.completion_tokens or 0
        model_name = usage.model or model_name
        vision_ms += ms
    usage = UsageInfo(
        prompt_tokens=total_prompt or None,
        completion_tokens=total_completion or None,
        model=model_name,
    )
    joined = "\n\n".join(vision_texts) if vision_texts else None
    return all_params, usage, warnings, joined, vision_ms


@router.post(
    "/ocr/extract",
    response_model=OcrExtractResponse,
    summary="Extract lab metrics (default: free OCR, 0 token)",
)
async def ocr_extract(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    language: str | None = Form(None),
    request_id: str | None = Form(None),
    include_bbox: str | bool = Form("true"),
    include_summary: str | bool = Form("false"),
    settings: Settings = Depends(get_settings),
) -> OcrExtractResponse:
    rid = request_id or str(uuid.uuid4())
    if rid == "string":
        rid = str(uuid.uuid4())
    want_bbox = _parse_bool(include_bbox, True)
    want_summary = _parse_bool(include_summary, False)

    content = await file.read()
    if not content:
        raise AppError(ErrorCode.INVALID_FILE, "Empty file.", status_code=400, request_id=rid)
    if len(content) > settings.max_file_bytes:
        raise AppError(ErrorCode.INVALID_FILE, "File exceeds size limit.", status_code=400, request_id=rid)

    warnings: list[str] = []
    ai = AiService(settings)
    from app.core.runtime_config import effective_extract_mode

    mode = effective_extract_mode(settings.extract_mode or "free")

    ocr_ms = 0
    ocr_confidence = 0.0
    redacted_text = ""
    word_boxes: list[WordBox] = []
    params: list[ExtractedParameter] = []
    ai_usage = UsageInfo(model="heuristic", prompt_tokens=0, completion_tokens=0)
    ai_ms = 0

    need_ocr = mode in {"free", "ocr", "ocr_first"} or (
        mode in {"vision", "hybrid"} and settings.run_ocr_with_vision
    )
    if need_ocr:
        try:
            ocr_result = OcrService(settings).extract(
                content, file.filename or "upload", file.content_type, language
            )
            ocr_ms = ocr_result.ocr_ms
            ocr_confidence = ocr_result.confidence
            warnings.append(f"ocr_engine:{ocr_result.engine}")
            redacted_text, pii_found = redact_pii(ocr_result.text)
            if pii_found:
                warnings.append("pii_redacted")
            for page in ocr_result.pages:
                word_boxes.extend(page.word_boxes)
        except AppError as e:
            if mode in {"free", "ocr", "ocr_first"}:
                e.request_id = rid
                raise
            warnings.append(f"ocr_skipped:{e.code}")

    if mode == "free":
        if not redacted_text:
            raise AppError(ErrorCode.OCR_FAILED, "No OCR text available.", status_code=422, request_id=rid)
        params = _local_extract(redacted_text, word_boxes, document_type.value, settings.confidence_verify_threshold, content, file.filename or "upload")
        warnings.append("extract_mode:free")
        warnings.append("tokens:0")
        if params:
            warnings.append("layout:lexicon_abc_or_column_bands")
        else:
            warnings.append("no_metrics_matched")
            warnings.append("hint:free_mode_layout_hard_or_watermark")

    elif mode == "ocr":
        if not redacted_text:
            raise AppError(ErrorCode.OCR_FAILED, "No OCR text available.", status_code=422, request_id=rid)
        # Prefer Gemini text if available; else local table+heuristic
        if ai.available:
            params, ai_usage, ai_ms = ai.extract_parameters(redacted_text, document_type.value)
            local = _local_extract(redacted_text, word_boxes, document_type.value, settings.confidence_verify_threshold, content, file.filename or "upload")
            params = merge_extracts(params, local)
            warnings.append("extract_mode:ocr_gemini_text")
        else:
            params = _local_extract(redacted_text, word_boxes, document_type.value, settings.confidence_verify_threshold, content, file.filename or "upload")
            warnings.append("extract_mode:ocr_heuristic")
            warnings.append("tokens:0")

    elif mode == "ocr_first":
        if not redacted_text:
            raise AppError(ErrorCode.OCR_FAILED, "No OCR text available.", status_code=422, request_id=rid)
        params = _local_extract(redacted_text, word_boxes, document_type.value, settings.confidence_verify_threshold, content, file.filename or "upload")
        filled = _filled_count(params)
        need_vision = ai.available and (
            ocr_confidence < settings.vision_fallback_min_confidence
            or filled < settings.vision_fallback_min_values
        )
        if need_vision:
            try:
                params, ai_usage, w, vtext, ai_ms = _run_vision(
                    ai, settings, content, file.filename or "upload", file.content_type, document_type.value
                )
                # Keep strong local values if vision missed a field
                local = _local_extract(redacted_text, word_boxes, document_type.value, settings.confidence_verify_threshold, content, file.filename or "upload")
                params = merge_extracts(params, local)
                warnings.extend(w)
                if vtext and ocr_confidence < 0.6:
                    redacted_text, pii2 = redact_pii(vtext)
                    if pii2:
                        warnings.append("pii_redacted")
                warnings.append("extract_mode:ocr_first→vision")
            except AppError as e:
                warnings.append(f"vision_skipped:{e.code}")
                warnings.append("extract_mode:ocr_first_heuristic")
                warnings.append("tokens:0")
        else:
            warnings.append("extract_mode:ocr_first_heuristic")
            warnings.append("tokens:0")

    elif mode in {"vision", "hybrid"}:
        if not ai.available:
            if not redacted_text:
                raise AppError(ErrorCode.AI_FAILED, "Vision requires AI key; OCR also empty.", status_code=503, request_id=rid)
            params = _local_extract(redacted_text, word_boxes, document_type.value, settings.confidence_verify_threshold, content, file.filename or "upload")
            warnings.append("extract_mode:heuristic_no_ai_key")
            warnings.append("tokens:0")
        else:
            try:
                params, ai_usage, w, vtext, ai_ms = _run_vision(
                    ai, settings, content, file.filename or "upload", file.content_type, document_type.value
                )
                if redacted_text or word_boxes:
                    local = _local_extract(redacted_text, word_boxes, document_type.value, settings.confidence_verify_threshold, content, file.filename or "upload")
                    params = merge_extracts(params, local)
                warnings.extend(w)
                if vtext and (not redacted_text or ocr_confidence < 0.6):
                    redacted_text, pii2 = redact_pii(vtext)
                    if pii2:
                        warnings.append("pii_redacted")
                warnings.append("extract_mode:vision")
            except AppError as e:
                warnings.append(f"vision_failed:{e.code}")
                if redacted_text:
                    params = _local_extract(redacted_text, word_boxes, document_type.value, settings.confidence_verify_threshold, content, file.filename or "upload")
                    warnings.append("extract_mode:heuristic_fallback")
                    warnings.append("tokens:0")
                else:
                    e.request_id = rid
                    raise
    else:
        raise AppError(
            ErrorCode.INVALID_FILE,
            f"Unknown EXTRACT_MODE={mode}. Use free|ocr|ocr_first|vision.",
            status_code=400,
            request_id=rid,
        )

    blankish = any("blank_result" in w or "template_or_unfilled" in w for w in warnings)
    if blankish:
        params = [p for p in params if p.value is not None]
        if not params:
            warnings.append("no_filled_results")

    source_trace: dict = {}
    page_geometry = []
    if want_bbox and word_boxes and params:
        params, source_trace, page_geometry = attach_bboxes(params, word_boxes)
        unresolved = [p.key for p in params if p.bbox is None]
        if unresolved:
            warnings.append("bbox_unresolved:" + ",".join(unresolved))
    elif word_boxes:
        # Still expose page geometry for derivative coordinate space
        seen_pages: set[int] = set()
        from app.models.schemas import PageGeometry

        for wb in word_boxes:
            if wb.page in seen_pages or wb.page_width <= 0:
                continue
            seen_pages.add(wb.page)
            page_geometry.append(
                PageGeometry(
                    page=wb.page,
                    width=wb.page_width,
                    height=wb.page_height,
                    coordinate_space="derivative",
                )
            )

    summary_text = None
    summary_usage = UsageInfo()
    if want_summary:
        # free / ocr_first-heuristic: local summary (0 token)
        use_ai_summary = mode not in {"free"} and "tokens:0" not in warnings and ai.available
        if mode == "ocr_first" and any("heuristic" in w for w in warnings):
            use_ai_summary = False
        summary_text, summary_usage = ai.summarize(
            {}, {}, params, [document_type.value], use_ai=use_ai_summary
        )
        summary_text = strip_clinical_advice(summary_text or "")
        if not use_ai_summary:
            warnings.append("summary:local")
        if summary_usage.prompt_tokens:
            ai_usage.prompt_tokens = (ai_usage.prompt_tokens or 0) + (summary_usage.prompt_tokens or 0)
        if summary_usage.completion_tokens:
            ai_usage.completion_tokens = (ai_usage.completion_tokens or 0) + (summary_usage.completion_tokens or 0)

    usage = UsageInfo(
        ocr_ms=ocr_ms or None,
        ai_ms=ai_ms or None,
        prompt_tokens=ai_usage.prompt_tokens,
        completion_tokens=ai_usage.completion_tokens,
        model=ai_usage.model or summary_usage.model,
    )

    seen: set[str] = set()
    uniq_warnings: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            uniq_warnings.append(w)

    return OcrExtractResponse(
        request_id=rid,
        document_type=document_type,
        raw_ocr_text=redacted_text,
        ocr_confidence=ocr_confidence,
        extracted_parameters=params,
        source_trace_map=source_trace,
        page_geometry=page_geometry,
        coordinate_space="derivative",
        ai_summary_30s=summary_text,
        usage=usage,
        warnings=uniq_warnings,
    )


@router.post(
    "/analyze/summary",
    response_model=SummaryResponse,
    summary="30s executive summary (anonymized JSON)",
)
async def analyze_summary(
    body: SummaryRequest,
    settings: Settings = Depends(get_settings),
) -> SummaryResponse:
    rid = body.request_id or str(uuid.uuid4())
    if rid == "string":
        rid = str(uuid.uuid4())
    notes = body.layer1_clinical_notes or {}
    if body.b2_clinical_notes:
        notes = {**notes, "b2_clinical_notes": body.b2_clinical_notes}
    blob = " ".join(str(v) for v in notes.values())
    _, pii = redact_pii(blob)
    if pii:
        notes = {k: (redact_pii(str(v))[0] if isinstance(v, str) else v) for k, v in notes.items()}

    verified = body.verified_parameters or body.layer2_clinical_data or {}

    ai = AiService(settings)
    text, usage = ai.summarize(
        notes,
        verified,
        body.extracted_parameters,
        body.document_hints,
        verified_parameters=verified,
        b2_clinical_notes=body.b2_clinical_notes,
        anonymous_patient_token=body.anonymous_patient_token,
    )
    return SummaryResponse(
        request_id=rid,
        correlation_id=body.correlation_id,
        anonymous_patient_token=body.anonymous_patient_token,
        ai_summary_30s=strip_clinical_advice(text),
        usage=usage,
    )


@router.post("/admin/runtime-config", summary="Push extract_mode + LLM keys from clinic-booking")
async def admin_runtime_config(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    from app.core.runtime_config import set_override

    try:
        payload = await request.json()
    except Exception as e:
        raise AppError(ErrorCode.INVALID_FILE, "Invalid JSON body.", status_code=400) from e
    if not isinstance(payload, dict):
        raise AppError(ErrorCode.INVALID_FILE, "Expected JSON object.", status_code=400)

    saved = set_override(payload)
    # Never echo secrets back
    return {
        "ok": True,
        "extract_mode": saved.get("extract_mode"),
        "preferred_provider": saved.get("preferred_provider"),
        "gemini_model": saved.get("gemini_model"),
        "openai_model": saved.get("openai_model"),
        "ai_enabled": saved.get("ai_enabled"),
        "has_gemini_key": bool(saved.get("gemini_api_key")),
        "has_openai_key": bool(saved.get("openai_api_key")),
        "env_extract_mode_default": settings.extract_mode,
    }
