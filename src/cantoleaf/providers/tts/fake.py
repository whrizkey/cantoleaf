import math
from pathlib import Path

import numpy as np
import soundfile as sf

from cantoleaf.models import SynthesizedSpan, Utterance, WordTiming
from cantoleaf.providers.base import TtsProvider, Voice


class FakeTtsProvider(TtsProvider):
    """
    Deterministic offline fake TTS provider:
    Synthesizes a soft sine tone proportional to word count and computes exact synthetic word timings.
    """

    name: str = "fake"
    sample_rate: int = 24000
    default_voice: str = "fake_voice_1"

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path("/tmp/cantoleaf_fake_tts")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def list_voices(self, language: str = "en") -> list[Voice]:
        return [
            Voice(
                voice_id="fake_voice_1", name="Fake Narrator", language=language, provider="fake"
            ),
            Voice(voice_id="fake_voice_2", name="Fake Whisper", language=language, provider="fake"),
        ]

    async def synthesize(
        self,
        utterance: Utterance,
        *,
        voice: str | None = None,
        rate: float = 1.0,
    ) -> SynthesizedSpan:
        words = utterance.spoken_text.split()
        if not words:
            words = ["..."]

        # Approximate duration: ~250ms per word
        word_dur = 0.25 / max(0.25, rate)
        duration_sec = len(words) * word_dur

        # Generate a gentle 440 Hz sine tone
        t = np.linspace(
            0, duration_sec, int(self.sample_rate * duration_sec), endpoint=False, dtype=np.float32
        )
        # Apply soft attack and release envelope
        fade_len = min(int(self.sample_rate * 0.02), len(t) // 2)
        env = np.ones_like(t)
        if fade_len > 0:
            env[:fade_len] = np.linspace(0, 1, fade_len)
            env[-fade_len:] = np.linspace(1, 0, fade_len)
        audio = 0.2 * np.sin(2 * math.pi * 440 * t) * env

        # Safe filename hashing to prevent collisions across voices/rates
        import hashlib

        h = hashlib.sha256(f"{utterance.utterance_id}:{voice}:{rate:.2f}".encode()).hexdigest()[:12]
        out_path = self.cache_dir / f"{utterance.utterance_id.replace(':', '_')}_{h}.wav"
        sf.write(str(out_path), audio, self.sample_rate)

        # Generate exact synthetic WordTiming intervals
        word_timings: list[WordTiming] = []
        char_cursor = 0
        cur_t = 0.0

        for w in words:
            w_start = cur_t
            w_end = cur_t + word_dur
            c_start = utterance.spoken_text.find(w, char_cursor)
            if c_start == -1:
                c_start = char_cursor
            c_end = c_start + len(w)
            char_cursor = c_end

            word_timings.append(
                WordTiming(
                    word=w,
                    char_start=c_start,
                    char_end=c_end,
                    start_sec=round(w_start, 3),
                    end_sec=round(w_end, 3),
                )
            )
            cur_t += word_dur

        chosen_voice = voice or getattr(utterance, "target_voice", None) or "fake_voice_1"
        return SynthesizedSpan(
            utterance_id=utterance.utterance_id,
            audio_path=out_path,
            duration_sec=round(duration_sec, 3),
            pause_after_sec=utterance.pause_after_ms / 1000.0,
            word_timings=tuple(word_timings),
            provider=self.name,
            voice=chosen_voice,
        )
