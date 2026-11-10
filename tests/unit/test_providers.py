from pathlib import Path

import pytest

from cantoleaf.models import BlockKind, DepthGear, LangMode, Utterance
from cantoleaf.providers.registry import get_adapt_provider, get_tts_provider


@pytest.mark.asyncio
async def test_fake_tts_synthesis(tmp_path: Path) -> None:
    provider = get_tts_provider("fake")
    utterance = Utterance(
        utterance_id="book:ch0:b0:verbatim:source:u0",
        chapter_index=0,
        block_index=0,
        gear=DepthGear.VERBATIM,
        lang_mode=LangMode.SOURCE,
        block_kind=BlockKind.PROSE,
        source_text="Cognitive audio readers provide elastic depth.",
        spoken_text="Cognitive audio readers provide elastic depth.",
    )

    span = await provider.synthesize(utterance)
    assert span.duration_sec > 0.5
    assert len(span.word_timings) == 6
    assert span.audio_path.exists()
    assert span.word_timings[0].word == "Cognitive"
    assert span.word_timings[-1].word == "depth."


@pytest.mark.asyncio
async def test_extractive_adapter_gears() -> None:
    adapter = get_adapt_provider("extractive")
    text = "The linear book constraint traps readers on one rail. Eye reading allows selective skimming. Multi-rail audio frees the listener."

    pulse = await adapter.adapt_depth(text, DepthGear.PULSE)
    assert pulse == "The linear book constraint traps readers on one rail."

    crux = await adapter.adapt_depth(text, DepthGear.CRUX)
    assert "linear book constraint" in crux
    assert "Multi-rail audio frees the listener." in crux
