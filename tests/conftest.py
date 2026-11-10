"""Pytest configuration and shared fixtures for CantoLeaf."""

import pytest

from cantoleaf.config import AdaptProviderName, Settings, TtsProviderName


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        CANTOLEAF_TTS_PROVIDER=TtsProviderName.FAKE,
        CANTOLEAF_ADAPT_PROVIDER=AdaptProviderName.FAKE,
        CANTOLEAF_MAX_COST_USD=10.0,
    )
