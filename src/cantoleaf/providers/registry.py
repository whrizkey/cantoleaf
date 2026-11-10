from cantoleaf.config import get_settings
from cantoleaf.errors import ProviderError
from cantoleaf.providers.adapt.anthropic import AnthropicAdaptProvider
from cantoleaf.providers.adapt.deepl import DeeplAdaptProvider
from cantoleaf.providers.adapt.extractive import ExtractiveAdaptProvider
from cantoleaf.providers.adapt.openai_compat import OpenAiCompatAdaptProvider
from cantoleaf.providers.base import AdaptProvider, TtsProvider
from cantoleaf.providers.tts.elevenlabs import ElevenLabsTtsProvider
from cantoleaf.providers.tts.fake import FakeTtsProvider
from cantoleaf.providers.tts.openai_compat import OpenAiCompatTtsProvider


def get_tts_provider(name: str) -> TtsProvider:
    """Returns an instantiated TtsProvider by name."""
    normalized = name.lower().strip()
    settings = get_settings()
    provider_cache_dir = settings.cantoleaf_cache_dir / normalized

    if normalized == "fake":
        return FakeTtsProvider(cache_dir=provider_cache_dir)
    if normalized == "edge":
        try:
            from cantoleaf.providers.tts.edge import EdgeTtsProvider

            return EdgeTtsProvider(cache_dir=provider_cache_dir)
        except ImportError as e:
            raise ProviderError(
                "Edge TTS requires 'edge-tts'. Install with: pip install cantoleaf[tts]"
            ) from e
    if normalized == "elevenlabs":
        return ElevenLabsTtsProvider(
            api_key=settings.elevenlabs_api_key,
            model_id=settings.elevenlabs_model_id,
            cache_dir=provider_cache_dir,
        )
    if normalized in ("openai", "openai_compat"):
        return OpenAiCompatTtsProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            cache_dir=provider_cache_dir,
        )

    raise ProviderError(f"TTS provider '{name}' is not yet implemented or unrecognized.")


def get_adapt_provider(name: str) -> AdaptProvider:
    """Returns an instantiated AdaptProvider by name."""
    normalized = name.lower().strip()
    settings = get_settings()

    if normalized in ("extractive", "fake"):
        return ExtractiveAdaptProvider()
    if normalized in ("openai", "openai_compat"):
        return OpenAiCompatAdaptProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.cantoleaf_adapt_model or "gpt-4o-mini",
        )
    if normalized == "anthropic":
        return AnthropicAdaptProvider(
            api_key=settings.anthropic_api_key,
            model=settings.cantoleaf_adapt_model or "claude-3-5-haiku-20241022",
        )
    if normalized == "deepl":
        return DeeplAdaptProvider(api_key=settings.deepl_api_key)

    raise ProviderError(f"Adapt provider '{name}' is not yet implemented or unrecognized.")
