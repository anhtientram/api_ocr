"""Runtime overrides pushed from clinic-booking admin UI (encrypted keys stay in CRM DB;
proxy receives plaintext over HMAC channel for process-local use only)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_OVERRIDE: dict[str, Any] = {}
_OVERRIDE_PATH = Path("/tmp/api_ocr_runtime_config.json")


def load_override() -> dict[str, Any]:
    global _OVERRIDE
    with _LOCK:
        if _OVERRIDE:
            return dict(_OVERRIDE)
        if _OVERRIDE_PATH.exists():
            try:
                data = json.loads(_OVERRIDE_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    _OVERRIDE = data
                    return dict(_OVERRIDE)
            except Exception:
                return {}
        return {}


def set_override(payload: dict[str, Any]) -> dict[str, Any]:
    global _OVERRIDE
    clean = {
        "extract_mode": (payload.get("extract_mode") or "free").strip().lower(),
        "preferred_provider": (payload.get("preferred_provider") or "gemini").strip().lower(),
        "gemini_api_key": (payload.get("gemini_api_key") or "").strip() or None,
        "openai_api_key": (payload.get("openai_api_key") or "").strip() or None,
        "gemini_model": (payload.get("gemini_model") or "").strip() or None,
        "openai_model": (payload.get("openai_model") or "").strip() or None,
        "ai_enabled": bool(payload.get("ai_enabled", True)),
    }
    with _LOCK:
        _OVERRIDE = clean
        try:
            _OVERRIDE_PATH.write_text(json.dumps(clean), encoding="utf-8")
        except Exception:
            pass
    return dict(clean)


def effective_extract_mode(default: str) -> str:
    ov = load_override()
    mode = (ov.get("extract_mode") or default or "free").strip().lower()
    return mode


def effective_api_key(default_key: str, provider: str = "gemini") -> str:
    ov = load_override()
    if provider == "openai":
        return (ov.get("openai_api_key") or default_key or "").strip()
    return (ov.get("gemini_api_key") or default_key or "").strip()


def effective_model(default_model: str, provider: str = "gemini") -> str:
    ov = load_override()
    if provider == "openai":
        return (ov.get("openai_model") or default_model or "").strip()
    return (ov.get("gemini_model") or default_model or "").strip()
