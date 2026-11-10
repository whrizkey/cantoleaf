from pathlib import Path

import pytest

from cantoleaf.models import BlockKind, DepthGear, LangMode, Utterance
from cantoleaf.pipeline.cache import AudioCache
from cantoleaf.pipeline.synthesizer import SynthesisPipeline
from cantoleaf.providers.tts.fake import FakeTtsProvider
from cantoleaf.workflows.earcons import generate_heading_chime, generate_quote_pluck


def test_earcon_generation() -> None:
    chime = generate_heading_chime(24000)
    assert len(chime) > 0
    assert float(chime.max()) <= 0.20

    pluck = generate_quote_pluck(24000)
    assert len(pluck) > 0


@pytest.mark.asyncio
async def test_synthesis_pipeline_and_cache(tmp_path: Path) -> None:
    cache = AudioCache(db_path=tmp_path / "test.db")
    tts = FakeTtsProvider(cache_dir=tmp_path / "audio")
    pipeline = SynthesisPipeline(tts, cache)

    heading_u = Utterance(
        utterance_id="book:ch0:b0:verbatim:source:u0",
        chapter_index=0,
        block_index=0,
        gear=DepthGear.VERBATIM,
        lang_mode=LangMode.SOURCE,
        block_kind=BlockKind.HEADING,
        source_text="Chapter 1: The Linear Constraint",
        spoken_text="Chapter 1: The Linear Constraint",
    )

    # 1st call: fresh synthesis with earcon
    span1 = await pipeline.synthesize_utterance(heading_u, enable_earcons=True)
    assert span1.duration_sec > 0.5
    assert span1.word_timings[0].start_sec > 0.0  # shifted due to earcon chime

    # 2nd call: instant cache hit
    span2 = await pipeline.synthesize_utterance(heading_u, enable_earcons=True)
    assert span2.duration_sec == span1.duration_sec
    assert span2.word_timings == span1.word_timings
