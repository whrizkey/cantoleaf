import logging
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_keyring(key_name: str) -> str:
    try:
        import keyring

        val = keyring.get_password("cantoleaf", key_name)
        return val or ""
    except Exception:
        return ""


class TtsProviderName(StrEnum):
    KOKORO = "kokoro"
    PIPER = "piper"
    EDGE = "edge"
    ELEVENLABS = "elevenlabs"
    OPENAI_COMPAT = "openai_compat"
    FAKE = "fake"


class AdaptProviderName(StrEnum):
    EXTRACTIVE = "extractive"
    OPENAI_COMPAT = "openai_compat"
    ANTHROPIC = "anthropic"
    DEEPL = "deepl"
    FAKE = "fake"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Provider selection
    cantoleaf_tts_provider: TtsProviderName = Field(
        default=TtsProviderName.EDGE,
        alias="CANTOLEAF_TTS_PROVIDER",
    )
    cantoleaf_tts_voice: str = Field(
        default="en-US-ChristopherNeural",
        alias="CANTOLEAF_TTS_VOICE",
    )
    cantoleaf_adapt_provider: AdaptProviderName = Field(
        default=AdaptProviderName.EXTRACTIVE,
        alias="CANTOLEAF_ADAPT_PROVIDER",
    )
    cantoleaf_adapt_model: str = Field(
        default="",
        alias="CANTOLEAF_ADAPT_MODEL",
    )

    # Cloud Credentials (BYOK) with keyring fallback
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    elevenlabs_api_key: str = Field(default="", alias="ELEVENLABS_API_KEY")
    elevenlabs_model_id: str = Field(default="eleven_multilingual_v2", alias="ELEVENLABS_MODEL_ID")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    deepl_api_key: str = Field(default="", alias="DEEPL_API_KEY")

    # Safety & Spend Protection
    cantoleaf_max_cost_usd: float = Field(default=5.00, alias="CANTOLEAF_MAX_COST_USD")

    # Paths & Logging
    cantoleaf_cache_dir: Path = Field(
        default=Path("~/.cantoleaf/cache").expanduser(),
        alias="CANTOLEAF_CACHE_DIR",
    )
    cantoleaf_log_level: str = Field(default="INFO", alias="CANTOLEAF_LOG_LEVEL")

    @field_validator("cantoleaf_cache_dir", mode="before")
    @classmethod
    def expand_cache_dir(cls, v: Any) -> Path:
        if isinstance(v, (str, Path)):
            return Path(v).expanduser()
        return Path("~/.cantoleaf/cache").expanduser()

    @field_validator(
        "openai_api_key", "elevenlabs_api_key", "anthropic_api_key", "deepl_api_key", mode="after"
    )
    @classmethod
    def fallback_to_keyring(cls, v: str, info: Any) -> str:
        if not v:
            return _read_keyring(info.field_name)
        return v


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def setup_logging(level: str | None = None) -> None:
    """Configures root logging according to cantoleaf_log_level."""
    settings = get_settings()
    lvl_name = (level or settings.cantoleaf_log_level).upper()
    lvl = getattr(logging, lvl_name, logging.INFO)
    logging.basicConfig(level=lvl, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
