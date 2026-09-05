from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ai-intake-proxy"
    app_env: str = "development"
    ai_proxy_secret: str = "dev-secret-change-me"

    max_file_bytes: int = 15 * 1024 * 1024
    max_pdf_pages: int = 20
    ocr_languages: str = "vie+eng"
    ocr_dpi: int = 200
    confidence_verify_threshold: float = 0.7

    ai_provider: str = "gemini"
    ai_api_key: str = ""
    gemini_api_key: str = ""
    ai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    ai_model: str = "gemini-2.5-flash"
    ai_timeout_seconds: float = 90.0
    ai_enabled: bool = True

    # Cost modes (cheapest → most accurate):
    #   free      = Tesseract + local heuristic only (0 Gemini token)  ← default tiết kiệm
    #   ocr       = OCR + Gemini text (rẻ, không gửi ảnh)
    #   ocr_first = table OCR trước; Vision chỉ khi thiếu chỉ số / OCR yếu  ← default cân bằng
    #   vision    = luôn Gemini Vision (tốn token nhất)
    extract_mode: str = "ocr_first"
    run_ocr_with_vision: bool = True
    vision_fallback_min_confidence: float = 0.78
    vision_fallback_min_values: int = 8

    temp_dir: str = "/tmp/api_ocr"

    @property
    def resolved_ai_api_key(self) -> str:
        return (self.gemini_api_key or self.ai_api_key or "").strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
