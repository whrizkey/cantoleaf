import numpy as np
import soundfile as sf

from cantoleaf.models import BlockKind, SynthesizedSpan, Utterance
from cantoleaf.pipeline.accounting import UsageTracker
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
    spend tracking, and SQLite cache lookups.
    """

    def __init__(
        self,
        tts_provider: TtsProvider,
        cache: AudioCache,
        usage_tracker: UsageTracker | None = None,
    ) -> None:
        self.tts = tts_provider
        self.cache = cache
        self.tracker = usage_tracker

    async def synthesize_utterance(
        self,
        utterance: Utterance,
        *,
        voice: str | None = None,
        secondary_voice: str | None = None,
        rate: float = 1.0,
        enable_earcons: bool = True,
    ) -> SynthesizedSpan:
        provider_default = getattr(self.tts, "default_voice", "default")
        if utterance.voice_role == "secondary_echo":
            chosen_voice = (
                secondary_voice or getattr(utterance, "target_voice", None) or provider_default
            )
        else:
            chosen_voice = voice or getattr(utterance, "target_voice", None) or provider_default

        # Check cache first with the exact concrete voice
        cached = self.cache.get(
            utterance.spoken_text,
            self.tts.name,
            chosen_voice,
            rate,
            block_kind=utterance.block_kind,
            enable_earcons=enable_earcons,
        )
        if cached:
            return cached

        # Enforce budget before cloud API call
        if self.tracker:
            self.tracker.record_tts_usage(self.tts.name, len(utterance.spoken_text))

        # Synthesize fresh clip with explicit concrete voice
        span = await self.tts.synthesize(utterance, voice=chosen_voice, rate=rate)

        # Prepend procedural earcon if applicable
        if enable_earcons and utterance.block_kind in (
            BlockKind.HEADING,
            BlockKind.QUOTE,
            BlockKind.TABLE,
        ):
            speech_data, sr = sf.read(str(span.audio_path))
            if speech_data.ndim > 1:
                speech_data = speech_data.mean(axis=1)

            # Generate earcon matched to the actual audio sample rate
            earcon_audio = None
            if utterance.block_kind == BlockKind.HEADING:
                earcon_audio = generate_heading_chime(sr)
            elif utterance.block_kind == BlockKind.QUOTE:
                earcon_audio = generate_quote_pluck(sr)
            elif utterance.block_kind == BlockKind.TABLE:
                earcon_audio = generate_figure_card_chime(sr)

            if earcon_audio is not None:
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

        # Store in cache with exact key parameters
        self.cache.put(
            utterance.spoken_text,
            rate,
            span,
            block_kind=utterance.block_kind,
            enable_earcons=enable_earcons,
        )
        return span
