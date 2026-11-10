from cantoleaf.errors import ProviderError
from cantoleaf.providers.adapt.extractive import ExtractiveAdaptProvider
from cantoleaf.providers.base import AdaptProvider, TtsProvider
from cantoleaf.providers.tts.edge import EdgeTtsProvider
from cantoleaf.providers.tts.fake import FakeTtsProvider


def get_tts_provider(name: str) -> TtsProvider:
    """Returns an instantiated TtsProvider by name."""
    normalized = name.lower().strip()
    if normalized == "fake":
        return FakeTtsProvider()
    if normalized == "edge":
        return EdgeTtsProvider()

    raise ProviderError(f"TTS provider '{name}' is not yet implemented or unrecognized.")


def get_adapt_provider(name: str) -> AdaptProvider:
    """Returns an instantiated AdaptProvider by name."""
    normalized = name.lower().strip()
    if normalized in ("extractive", "fake"):
        return ExtractiveAdaptProvider()

    raise ProviderError(f"Adapt provider '{name}' is not yet implemented or unrecognized.")
