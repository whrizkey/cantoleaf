from pathlib import Path

import httpx

from cantoleaf.errors import ProviderError
from cantoleaf.models import SynthesizedSpan, Utterance, WordTiming
from cantoleaf.providers.base import TtsProvider, Voice


class OpenAiCompatTtsProvider(TtsProvider):
    """
    OpenAI-Compatible TTS Provider:
    Works with official OpenAI (/v1/audio/speech), Groq, LocalAI, and Kokoro-FastAPI.
    """

    name: str = "openai_compat"
    sample_rate: int = 24000

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        cache_dir: Path | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.cache_dir = cache_dir or Path("~/.cantoleaf/cache/openai_tts").expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def list_voices(self, language: str = "en") -> list[Voice]:
        return [
            Voice(voice_id="alloy", name="Alloy", language="en", provider=self.name),
            Voice(voice_id="echo", name="Echo", language="en", provider=self.name),
            Voice(voice_id="fable", name="Fable", language="en", provider=self.name),
            Voice(voice_id="onyx", name="Onyx", language="en", provider=self.name),
            Voice(voice_id="nova", name="Nova", language="en", provider=self.name),
            Voice(voice_id="shimmer", name="Shimmer", language="en", provider=self.name),
        ]

    async def synthesize(
        self,
        utterance: Utterance,
        *,
        voice: str | None = None,
        rate: float = 1.0,
    ) -> SynthesizedSpan:
        if not self.api_key:
            raise ProviderError("OpenAI API key is missing. Set OPENAI_API_KEY in .env or keyring.")

        url = f"{self.base_url}/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        chosen_voice = voice or "alloy"
        payload = {
            "model": "tts-1",
            "input": utterance.spoken_text,
            "voice": chosen_voice,
            "speed": rate,
            "response_format": "mp3",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 429:
                raise ProviderError("OpenAI rate limit exceeded (429)", retryable=True)
            if resp.status_code != 200:
                raise ProviderError(
                    f"OpenAI TTS synthesis failed ({resp.status_code}): {resp.text}"
                )
            audio_bytes = resp.content

        out_path = self.cache_dir / f"{utterance.utterance_id.replace(':', '_')}.mp3"
        out_path.write_bytes(audio_bytes)

        # Interpolate syllable/character timings
        words = utterance.spoken_text.split()
        dur_sec = max(0.6, len(words) * 0.28 / max(0.25, rate))
        word_dur = dur_sec / max(1, len(words))

        word_timings: list[WordTiming] = []
        c_idx = 0
        t_cur = 0.0
        for w in words:
            s_idx = utterance.spoken_text.find(w, c_idx)
            e_idx = s_idx + len(w) if s_idx != -1 else c_idx + len(w)
            c_idx = e_idx
            word_timings.append(
                WordTiming(
                    word=w,
                    char_start=s_idx,
                    char_end=e_idx,
                    start_sec=round(t_cur, 3),
                    end_sec=round(t_cur + word_dur, 3),
                )
            )
            t_cur += word_dur

        return SynthesizedSpan(
            utterance_id=utterance.utterance_id,
            audio_path=out_path,
            duration_sec=round(dur_sec, 3),
            pause_after_sec=utterance.pause_after_ms / 1000.0,
            word_timings=tuple(word_timings),
            provider=self.name,
            voice=chosen_voice,
        )
