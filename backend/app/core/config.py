from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SmartMOM API"
    environment: str = "development"
    port: int = 3001
    database_url: str = "sqlite:///./.data/smartmom.db"
    jwt_secret: str = "development-only-change-me"
    jwt_expiry_hours: int = 8
    client_origin: str = "http://localhost:5173"
    upload_dir: Path = Path("./uploads")
    max_upload_mb: int = 200
    transcription_provider: str = "local"
    minutes_provider: str = "local"
    openai_api_key: str | None = None
    openai_transcription_model: str = "gpt-4o-transcribe-diarize"
    openai_summary_model: str = "gpt-5-mini"
    whisper_cpp_path: Path = Path("./tools/whisper/whisper-cli.exe")
    whisper_model_path: Path = Path("./models/ggml-small.en-tdrz.bin")
    whisper_language: str = "en"
    local_minutes_model: str = "Qwen/Qwen2.5-1.5B-Instruct"
    local_sentiment_model: str = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"
    local_minutes_max_tokens: int = 700

    @property
    def database_mode(self) -> str:
        return "postgresql" if self.database_url.startswith("postgresql") else "sqlite"


@lru_cache
def get_settings() -> Settings:
    return Settings()
