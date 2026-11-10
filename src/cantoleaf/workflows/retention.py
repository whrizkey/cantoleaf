from cantoleaf.models import BlockKind, DepthGear, LangMode, Utterance
from cantoleaf.providers.base import AdaptProvider


async def generate_recall_lock_utterances(
    book_id: str,
    chapter_index: int,
    chapter_title: str,
    chapter_summary: str,
    adapt_provider: AdaptProvider,
) -> list[Utterance]:
    """
    Workflow 4: Generates interactive Socratic Memory Locks at chapter boundaries:
    1. Announces the Memory Lock with a soft chime
    2. Speaks the retrieval question
    3. Inserts a 4-second thinking pulse (recall_tick) for active cognitive retrieval
    4. Speaks the concise answer before advancing to the next chapter.
    """
    qa_pairs = await adapt_provider.generate_recall_questions(chapter_title, chapter_summary)
    if not qa_pairs:
        return []

    utterances: list[Utterance] = []
    u_idx = 0

    # Intro prompt
    utterances.append(
        Utterance(
            utterance_id=f"{book_id}:ch{chapter_index}:recall:intro",
            chapter_index=chapter_index,
            block_index=9999,
            gear=DepthGear.PULSE,
            lang_mode=LangMode.SOURCE,
            block_kind=BlockKind.RECALL_LOCK,
            source_text="Active Recall Checkpoint.",
            spoken_text="Active Recall Checkpoint. Test your memory on the chapter's core ideas.",
            voice_role="socratic_host",
            pause_after_ms=800,
        )
    )

    for u_idx, (q, a) in enumerate(qa_pairs):
        # Question
        utterances.append(
            Utterance(
                utterance_id=f"{book_id}:ch{chapter_index}:recall:q:{u_idx}",
                chapter_index=chapter_index,
                block_index=9999,
                gear=DepthGear.PULSE,
                lang_mode=LangMode.SOURCE,
                block_kind=BlockKind.RECALL_LOCK,
                source_text=q,
                spoken_text=f"Question: {q}",
                voice_role="socratic_host",
                pause_after_ms=4000,  # 4-second thinking pause!
            )
        )
        # Answer
        utterances.append(
            Utterance(
                utterance_id=f"{book_id}:ch{chapter_index}:recall:a:{u_idx}",
                chapter_index=chapter_index,
                block_index=9999,
                gear=DepthGear.PULSE,
                lang_mode=LangMode.SOURCE,
                block_kind=BlockKind.RECALL_LOCK,
                source_text=a,
                spoken_text=f"Key takeaway: {a}",
                voice_role="socratic_host",
                pause_after_ms=1200,
            )
        )

    return utterances
