from cantoleaf.models import LangMode, Utterance
from cantoleaf.providers.base import AdaptProvider


async def weave_bilingual_stream(
    utterances: list[Utterance],
    lang_mode: LangMode,
    target_lang: str,
    adapt_provider: AdaptProvider,
) -> list[Utterance]:
    """
    Workflow 2: The Bilingual Bridge.
    Takes a base stream of utterances and weaves them into the chosen LangMode:
    - SOURCE: unaltered
    - TARGET: full translation
    - ECHO: sentence-by-sentence shadowing (Voice A says source, Voice B says translation)
    - CODE_SWITCH: translated prose with original domain terms preserved
    """
    if lang_mode == LangMode.SOURCE:
        return utterances

    weaved: list[Utterance] = []
    idx = 0

    for u in utterances:
        translated = await adapt_provider.translate(
            u.spoken_text,
            target_lang=target_lang,
            lang_mode=lang_mode,
        )

        if lang_mode == LangMode.TARGET or lang_mode == LangMode.CODE_SWITCH:
            weaved.append(
                Utterance(
                    utterance_id=f"{u.utterance_id}:tr{idx}",
                    chapter_index=u.chapter_index,
                    block_index=u.block_index,
                    gear=u.gear,
                    lang_mode=lang_mode,
                    block_kind=u.block_kind,
                    source_text=u.source_text,
                    spoken_text=translated,
                    voice_role="primary",
                    pause_after_ms=u.pause_after_ms,
                )
            )
            idx += 1

        elif lang_mode == LangMode.ECHO:
            # First: Source utterance (primary voice)
            weaved.append(
                Utterance(
                    utterance_id=f"{u.utterance_id}:echo_src:{idx}",
                    chapter_index=u.chapter_index,
                    block_index=u.block_index,
                    gear=u.gear,
                    lang_mode=lang_mode,
                    block_kind=u.block_kind,
                    source_text=u.source_text,
                    spoken_text=u.spoken_text,
                    voice_role="primary",
                    pause_after_ms=200,
                )
            )
            idx += 1
            # Second: Target shadow utterance (secondary_echo voice)
            weaved.append(
                Utterance(
                    utterance_id=f"{u.utterance_id}:echo_tgt:{idx}",
                    chapter_index=u.chapter_index,
                    block_index=u.block_index,
                    gear=u.gear,
                    lang_mode=lang_mode,
                    block_kind=u.block_kind,
                    source_text=u.source_text,
                    spoken_text=translated,
                    voice_role="secondary_echo",
                    pause_after_ms=u.pause_after_ms,
                )
            )
            idx += 1

    return weaved
