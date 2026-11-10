from cantoleaf.ingest.segmenter import split_into_sentences
from cantoleaf.models import BlockKind, Chapter, DepthGear, LangMode, Utterance
from cantoleaf.providers.base import AdaptProvider


async def generate_depth_stream(
    book_id: str,
    chapter: Chapter,
    gear: DepthGear,
    lang_mode: LangMode,
    adapt_provider: AdaptProvider,
) -> list[Utterance]:
    """
    Generates a sequence of Utterance objects for a given Chapter and DepthGear.
    All utterances retain their source `block_index` so listeners can shift
    gears mid-chapter seamlessly without losing their place.
    """
    utterances: list[Utterance] = []
    u_idx = 0

    if gear == DepthGear.VERBATIM:
        for block in chapter.blocks:
            sentences = split_into_sentences(block.text)
            for s in sentences:
                utterances.append(
                    Utterance(
                        utterance_id=f"{book_id}:ch{chapter.index}:b{block.block_index}:verbatim:{lang_mode}:u{u_idx}",
                        chapter_index=chapter.index,
                        block_index=block.block_index,
                        gear=DepthGear.VERBATIM,
                        lang_mode=lang_mode,
                        block_kind=block.kind,
                        source_text=s,
                        spoken_text=s,
                        pause_after_ms=350 if block.kind != BlockKind.HEADING else 800,
                    )
                )
                u_idx += 1

    elif gear == DepthGear.CRUX:
        # Crux preserves headings and core arguments verbatim, but bridges anecdotes
        for block in chapter.blocks:
            if block.kind == BlockKind.ANECDOTE:
                bridge_text = f"[Case summary: {block.text[:120]}...]"
                utterances.append(
                    Utterance(
                        utterance_id=f"{book_id}:ch{chapter.index}:b{block.block_index}:crux:{lang_mode}:u{u_idx}",
                        chapter_index=chapter.index,
                        block_index=block.block_index,
                        gear=DepthGear.CRUX,
                        lang_mode=lang_mode,
                        block_kind=BlockKind.ANECDOTE,
                        source_text=block.text,
                        spoken_text=bridge_text,
                        pause_after_ms=500,
                    )
                )
                u_idx += 1
            else:
                sentences = split_into_sentences(block.text)
                for s in sentences:
                    utterances.append(
                        Utterance(
                            utterance_id=f"{book_id}:ch{chapter.index}:b{block.block_index}:crux:{lang_mode}:u{u_idx}",
                            chapter_index=chapter.index,
                            block_index=block.block_index,
                            gear=DepthGear.CRUX,
                            lang_mode=lang_mode,
                            block_kind=block.kind,
                            source_text=s,
                            spoken_text=s,
                            pause_after_ms=350 if block.kind != BlockKind.HEADING else 800,
                        )
                    )
                    u_idx += 1

    elif gear == DepthGear.PULSE:
        # Pulse synthesizes the core thesis / topic statement per section
        for block in chapter.blocks:
            if block.kind in (BlockKind.HEADING, BlockKind.PROSE):
                adapted = await adapt_provider.adapt_depth(block.text, DepthGear.PULSE)
                if adapted:
                    utterances.append(
                        Utterance(
                            utterance_id=f"{book_id}:ch{chapter.index}:b{block.block_index}:pulse:{lang_mode}:u{u_idx}",
                            chapter_index=chapter.index,
                            block_index=block.block_index,
                            gear=DepthGear.PULSE,
                            lang_mode=lang_mode,
                            block_kind=block.kind,
                            source_text=block.text,
                            spoken_text=adapted,
                            pause_after_ms=600,
                        )
                    )
                    u_idx += 1

    return utterances
