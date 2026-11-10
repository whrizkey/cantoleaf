from cantoleaf.config import get_settings
from cantoleaf.errors import ProviderError
from cantoleaf.providers.adapt.extractive import ExtractiveAdaptProvider
from cantoleaf.providers.base import AdaptProvider, TtsProvider
from cantoleaf.providers.tts.edge import EdgeTtsProvider
from cantoleaf.providers.tts.elevenlabs import ElevenLabsTtsProvider
from cantoleaf.providers.tts.fake import FakeTtsProvider
from cantoleaf.providers.tts.openai_compat import OpenAiCompatTtsProvider


def get_tts_provider(name: str) -> TtsProvider:
    """Returns an instantiated TtsProvider by name."""
    normalized = name.lower().strip()
    settings = get_settings()

    if normalized == "fake":
        return FakeTtsProvider()
    if normalized == "edge":
        return EdgeTtsProvider()
    if normalized == "elevenlabs":
        return ElevenLabsTtsProvider(
            api_key=settings.elevenlabs_api_key, model_id=settings.elevenlabs_model_id
        )
    if normalized in ("openai", "openai_compat"):
        return OpenAiCompatTtsProvider(
            api_key=settings.openai_api_key, base_url=settings.openai_base_url
        )

    raise ProviderError(f"TTS provider '{name}' is not yet implemented or unrecognized.")


def get_adapt_provider(name: str) -> AdaptProvider:
    """Returns an instantiated AdaptProvider by name."""
    normalized = name.lower().strip()
    if normalized in ("extractive", "fake"):
        return ExtractiveAdaptProvider()

    raise ProviderError(f"Adapt provider '{name}' is not yet implemented or unrecognized.")
