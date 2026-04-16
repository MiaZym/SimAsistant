from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TRANSCRIBE_URL: str = "http://host.docker.internal:8077/api/v1/transcribe"
    TRANSCRIBE_FILE_FIELD: str = "audio_file"

    DEFAULT_OLLAMA_URL: str = "http://host.docker.internal:11434"
    DEFAULT_VLLM_URL: str = "http://host.docker.internal:8000"
    VLLM_API_KEY: str | None = None

    LLM_TIMEOUT_SEC: int = 600

    # Pydantic v2: нельзя одновременно использовать "Config" и "model_config".
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

