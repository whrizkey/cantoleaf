import numpy as np
import soundfile as sf

from cantoleaf.models import BlockKind, SynthesizedSpan, Utterance
from cantoleaf.pipeline.cache import AudioCache
from cantoleaf.providers.base import TtsProvider
from cantoleaf.workflows.earcons import (
    generate_figure_card_chime,
    generate_heading_chime,
    generate_quote_pluck,
)


class SynthesisPipeline:
    """
    Coordinates TTS execution, procedural earcon prefixing/suffixing,
    and SQLite cache lookups.
    """

    def __init__(self, tts_provider: TtsProvider, cache: AudioCache) -> None:
        self.tts = tts_provider
        self.cache = cache

    async def synthesize_utterance(
        self,
        utterance: Utterance,
        *,
        voice: str | None = None,
        rate: float = 1.0,
        enable_earcons: bool = True,
    ) -> SynthesizedSpan:
        # Check cache first
        cached = self.cache.get(utterance.spoken_text, self.tts.name, voice or "default", rate)
        if cached:
            return cached

        # Synthesize fresh clip
        span = await self.tts.synthesize(utterance, voice=voice, rate=rate)

        # Prepend procedural earcon if applicable
        if enable_earcons and utterance.block_kind in (
            BlockKind.HEADING,
            BlockKind.QUOTE,
            BlockKind.TABLE,
        ):
            earcon_audio = None
            if utterance.block_kind == BlockKind.HEADING:
                earcon_audio = generate_heading_chime(self.tts.sample_rate)
            elif utterance.block_kind == BlockKind.QUOTE:
                earcon_audio = generate_quote_pluck(self.tts.sample_rate)
            elif utterance.block_kind == BlockKind.TABLE:
                earcon_audio = generate_figure_card_chime(self.tts.sample_rate)

            if earcon_audio is not None:
                speech_data, sr = sf.read(str(span.audio_path))
                if speech_data.ndim > 1:
                    speech_data = speech_data.mean(axis=1)

                combined = np.concatenate([earcon_audio, speech_data]).astype(np.float32)
                sf.write(str(span.audio_path), combined, sr)

                earcon_offset = len(earcon_audio) / float(sr)
                # Shift word timings by earcon offset
                shifted_timings = tuple(
                    wt.__class__(
                        word=wt.word,
                        char_start=wt.char_start,
                        char_end=wt.char_end,
                        start_sec=round(wt.start_sec + earcon_offset, 3),
                        end_sec=round(wt.end_sec + earcon_offset, 3),
                    )
                    for wt in span.word_timings
                )
                span = SynthesizedSpan(
                    utterance_id=span.utterance_id,
                    audio_path=span.audio_path,
                    duration_sec=round(span.duration_sec + earcon_offset, 3),
                    pause_after_sec=span.pause_after_sec,
                    word_timings=shifted_timings,
                    provider=span.provider,
                    voice=span.voice,
                )

        # Store in cache
        self.cache.put(utterance.spoken_text, rate, span)
        return span
