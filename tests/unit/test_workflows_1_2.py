import pytest

from cantoleaf.models import BlockKind, Chapter, DepthGear, LangMode, SemanticBlock
from cantoleaf.providers.adapt.extractive import ExtractiveAdaptProvider
from cantoleaf.workflows.bilingual_bridge import weave_bilingual_stream
from cantoleaf.workflows.depth_gears import generate_depth_stream


@pytest.fixture
def sample_chapter() -> Chapter:
    return Chapter(
        index=0,
        title="Chapter 1: The Linear Constraint",
        blocks=(
            SemanticBlock(
                block_index=0, kind=BlockKind.HEADING, text="Chapter 1: The Linear Constraint"
            ),
            SemanticBlock(
                block_index=1,
                kind=BlockKind.PROSE,
                text="For centuries, books preserved a single linear rail. Readers marched in lockstep.",
            ),
            SemanticBlock(
                block_index=2,
                kind=BlockKind.ANECDOTE,
                text="For example, when ancient Roman orators delivered speeches, they walked memory palaces.",
            ),
        ),
        estimated_chars=250,
    )


@pytest.mark.asyncio
async def test_depth_gears_shared_block_index(sample_chapter: Chapter) -> None:
    adapt = ExtractiveAdaptProvider()
    verbatim_stream = await generate_depth_stream(
        "book1", sample_chapter, DepthGear.VERBATIM, LangMode.SOURCE, adapt
    )
    crux_stream = await generate_depth_stream(
        "book1", sample_chapter, DepthGear.CRUX, LangMode.SOURCE, adapt
    )

    # In verbatim, block 1 produces 2 sentences
    assert any(u.block_index == 1 for u in verbatim_stream)

    # In crux, the anecdote at block 2 is replaced with a bridge, still anchored to block_index == 2
    anecdote_u = [u for u in crux_stream if u.block_index == 2]
    assert len(anecdote_u) == 1
    assert "[Case summary:" in anecdote_u[0].spoken_text


@pytest.mark.asyncio
async def test_bilingual_echo_mode(sample_chapter: Chapter) -> None:
    adapt = ExtractiveAdaptProvider()
    base_stream = await generate_depth_stream(
        "book1", sample_chapter, DepthGear.PULSE, LangMode.SOURCE, adapt
    )
    echo_stream = await weave_bilingual_stream(base_stream, LangMode.ECHO, "id", adapt)

    # Every base utterance generates 2 echo utterances (src + shadow tgt)
    assert len(echo_stream) == len(base_stream) * 2
    assert echo_stream[0].voice_role == "primary"
    assert echo_stream[1].voice_role == "secondary_echo"
    assert "[id]" in echo_stream[1].spoken_text
