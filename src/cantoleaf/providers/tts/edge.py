from pathlib import Path

try:
    import edge_tts
    from edge_tts.submaker import SubMaker

    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False
    edge_tts = None  # type: ignore
    SubMaker = None  # type: ignore

from cantoleaf.errors import ProviderError
from cantoleaf.models import SynthesizedSpan, Utterance, WordTiming
from cantoleaf.providers.base import TtsProvider, Voice


class EdgeTtsProvider(TtsProvider):
    """
    Microsoft Edge TTS Provider (Free, zero-key, high quality):
    Extracts native WordBoundary metadata for exact millisecond word highlighting.
    """

    name: str = "edge"
    sample_rate: int = 24000

    def __init__(self, cache_dir: Path | None = None) -> None:
        if not HAS_EDGE_TTS:
            raise ProviderError(
                "Edge TTS requires edge-tts. Install with: pip install cantoleaf[tts]"
            )
        self.cache_dir = cache_dir or Path("~/.cantoleaf/cache/edge").expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def list_voices(self, language: str = "en") -> list[Voice]:
        if not HAS_EDGE_TTS or edge_tts is None:
            raise ProviderError(
                "Edge TTS requires edge-tts. Install with: pip install cantoleaf[tts]"
            )
        try:
            voices = await edge_tts.list_voices()
        except Exception as e:
            raise ProviderError(f"Failed to fetch Edge TTS voices: {e}", retryable=True) from e

        results: list[Voice] = []
        for v in voices:
            locale = v.get("Locale", "")
            if language == "all" or locale.lower().startswith(language.lower()):
                results.append(
                    Voice(
                        voice_id=v.get("ShortName", ""),
                        name=v.get("FriendlyName", v.get("ShortName", "")),
                        language=locale,
                        gender=v.get("Gender", "neutral").lower(),
                        provider=self.name,
                    )
                )
        return results

    async def synthesize(
        self,
        utterance: Utterance,
        *,
        voice: str | None = None,
        rate: float = 1.0,
    ) -> SynthesizedSpan:
        if not HAS_EDGE_TTS or edge_tts is None or SubMaker is None:
            raise ProviderError(
                "Edge TTS requires edge-tts. Install with: pip install cantoleaf[tts]"
            )

        chosen_voice = voice or "en-US-ChristopherNeural"
        rate_str = f"{'+' if rate >= 1.0 else ''}{int((rate - 1.0) * 100)}%"

        out_path = self.cache_dir / f"{utterance.utterance_id.replace(':', '_')}.mp3"
        communicate = edge_tts.Communicate(
            text=utterance.spoken_text,
            voice=chosen_voice,
            rate=rate_str,
        )

        sub_maker = SubMaker()
        try:
            with open(out_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        sub_maker.feed(chunk)
        except Exception as e:
            raise ProviderError(
                f"Edge TTS synthesis failed for utterance {utterance.utterance_id}: {e}",
                retryable=True,
            ) from e

        # Extract word timings with cursor to correctly map repeated words
        word_timings: list[WordTiming] = []
        dur_sec = 0.0
        char_cursor = 0

        for cue in sub_maker.cues:
            start_s = cue.start.total_seconds()
            end_s = cue.end.total_seconds()
            dur_sec = max(dur_sec, end_s)

            c_start = utterance.spoken_text.find(cue.content, char_cursor)
            if c_start != -1:
                c_end = c_start + len(cue.content)
                char_cursor = c_end
            else:
                c_start = utterance.spoken_text.find(cue.content)
                c_end = c_start + len(cue.content) if c_start != -1 else 0

            word_timings.append(
                WordTiming(
                    word=cue.content,
                    char_start=c_start,
                    char_end=c_end,
                    start_sec=round(start_s, 3),
                    end_sec=round(end_s, 3),
                )
            )

        if not dur_sec:
            # Fallback based on words
            words = utterance.spoken_text.split()
            dur_sec = max(0.5, len(words) * (0.28 / max(0.25, rate)))

        return SynthesizedSpan(
            utterance_id=utterance.utterance_id,
            audio_path=out_path,
            duration_sec=round(dur_sec, 3),
            pause_after_sec=utterance.pause_after_ms / 1000.0,
            word_timings=tuple(word_timings),
            provider=self.name,
            voice=chosen_voice,
        )
