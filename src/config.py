from __future__ import annotations

import json
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _parse_headers(raw: str) -> dict[str, str]:
    """JSON-объект вида {"X-Gateway-Api-Key": "..."}; пусто/битый JSON -> {}."""
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if k and v}


class Settings(BaseSettings):
    # Транскрибация (опциональный внешний сервис)
    TRANSCRIBE_URL: str = "http://host.docker.internal:8077/api/v1/transcribe"
    TRANSCRIBE_FILE_FIELD: str = "file"

    # Провайдеры LLM по умолчанию.
    # В UI можно переопределить URL/API-ключ для custom OpenAI-compatible API.
    DEFAULT_OLLAMA_URL: str = "http://host.docker.internal:11434"
    DEFAULT_VLLM_URL: str = "http://host.docker.internal:8000"
    VLLM_API_KEY: str | None = None
    # Доп. заголовки для vLLM/OpenAI-совместимого API как JSON-строка.
    # Например для шлюза: {"X-Gateway-Api-Key": "..."}
    VLLM_EXTRA_HEADERS: str = ""

    DEFAULT_CUSTOM_URL: str = "https://api.openai.com"
    DEFAULT_CUSTOM_API_KEY: str | None = None
    DEFAULT_CUSTOM_MODELS: str = ""  # список моделей через запятую (fallback, если /v1/models недоступен)
    DEFAULT_CUSTOM_EXTRA_HEADERS: str = ""

    LLM_TIMEOUT_SEC: int = 600

    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    @property
    def custom_models(self) -> list[str]:
        return [m.strip() for m in self.DEFAULT_CUSTOM_MODELS.split(",") if m.strip()]

    def extra_headers_for(self, provider: str) -> dict[str, str]:
        raw = self.VLLM_EXTRA_HEADERS if provider == "vllm" else self.DEFAULT_CUSTOM_EXTRA_HEADERS
        return _parse_headers(raw)


settings = Settings()
