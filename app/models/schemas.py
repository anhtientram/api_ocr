from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.core.constants import DocumentType


class BBox(BaseModel):
    """Absolute pixel box on the derivative image (legacy / debug)."""

    x: int
    y: int
    w: int
    h: int


class NormalizedBBox(BaseModel):
    """Percent coordinates on the derivative image (Rev 0.2 Alpine Source Trace)."""

    x_pct: float
    y_pct: float
    w_pct: float
    h_pct: float


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
    bbox_norm: Optional[NormalizedBBox] = None


class UsageInfo(BaseModel):
    ocr_ms: Optional[int] = None
    ai_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    model: Optional[str] = None


class PageGeometry(BaseModel):
    page: int
    width: int
    height: int
    coordinate_space: str = "derivative"


class OcrExtractResponse(BaseModel):
    request_id: str
    document_type: DocumentType
    raw_ocr_text: str
    ocr_confidence: float
    extracted_parameters: List[ExtractedParameter] = Field(default_factory=list)
    source_trace_map: Dict[str, Any] = Field(default_factory=dict)
    page_geometry: List[PageGeometry] = Field(default_factory=list)
    coordinate_space: str = "derivative"
    ai_summary_30s: Optional[str] = None
    usage: UsageInfo = Field(default_factory=UsageInfo)
    warnings: List[str] = Field(default_factory=list)


class SummaryRequest(BaseModel):
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    anonymous_patient_token: Optional[str] = None
    # Pass 2 (Rev 0.2): B2 verified revision snapshot — preferred
    verified_parameters: Dict[str, Any] = Field(default_factory=dict)
    b2_clinical_notes: Optional[str] = None
    extracted_parameters: List[ExtractedParameter] = Field(default_factory=list)
    document_hints: List[str] = Field(default_factory=list)
    # Deprecated aliases (B1 draft names) — still accepted for transition
    layer1_clinical_notes: Dict[str, Any] = Field(default_factory=dict)
    layer2_clinical_data: Dict[str, Any] = Field(default_factory=dict)


class SummaryResponse(BaseModel):
    request_id: str
    correlation_id: Optional[str] = None
    anonymous_patient_token: Optional[str] = None
    ai_summary_30s: str
    usage: UsageInfo = Field(default_factory=UsageInfo)
