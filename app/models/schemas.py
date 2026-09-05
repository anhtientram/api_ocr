from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.core.constants import DocumentType


class BBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class ExtractedParameter(BaseModel):
    key: str
    label: str
    value: Optional[Union[float, str]] = None
    unit: Optional[str] = None
    raw_text: Optional[str] = None
    confidence: float = 0.0
    needs_human_verify: bool = False
    page: int = 0
    bbox: Optional[BBox] = None


class UsageInfo(BaseModel):
    ocr_ms: Optional[int] = None
    ai_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    model: Optional[str] = None


class OcrExtractResponse(BaseModel):
    request_id: str
    document_type: DocumentType
    raw_ocr_text: str
    ocr_confidence: float
    extracted_parameters: List[ExtractedParameter] = Field(default_factory=list)
    source_trace_map: Dict[str, Any] = Field(default_factory=dict)
    ai_summary_30s: Optional[str] = None
    usage: UsageInfo = Field(default_factory=UsageInfo)
    warnings: List[str] = Field(default_factory=list)


class SummaryRequest(BaseModel):
    request_id: Optional[str] = None
    layer1_clinical_notes: Dict[str, Any] = Field(default_factory=dict)
    layer2_clinical_data: Dict[str, Any] = Field(default_factory=dict)
    extracted_parameters: List[ExtractedParameter] = Field(default_factory=list)
    document_hints: List[str] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    request_id: str
    ai_summary_30s: str
    usage: UsageInfo = Field(default_factory=UsageInfo)
