import base64
from pathlib import Path

import httpx

from cantoleaf.errors import ProviderError
from cantoleaf.models import SynthesizedSpan, Utterance, WordTiming
from cantoleaf.providers.base import TtsProvider, Voice


class ElevenLabsTtsProvider(TtsProvider):
    """
    ElevenLabs BYOK Provider:
    Calls /v1/text-to-speech/{voice_id}/with-timestamps to capture exact character/word alignment.
    """

    name: str = "elevenlabs"
    sample_rate: int = 24000

    def __init__(
        self, api_key: str, model_id: str = "eleven_multilingual_v2", cache_dir: Path | None = None
    ) -> None:
        self.api_key = api_key
        self.model_id = model_id
        self.cache_dir = cache_dir or Path("~/.cantoleaf/cache/elevenlabs").expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def list_voices(self, language: str = "en") -> list[Voice]:
        if not self.api_key:
            return []
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": self.api_key}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise ProviderError(
                    f"ElevenLabs list_voices failed ({resp.status_code}): {resp.text}"
                )
            data = resp.json()
            return [
                Voice(
                    voice_id=v["voice_id"],
                    name=v["name"],
                    language=language,
                    provider=self.name,
                )
                for v in data.get("voices", [])
            ]

    async def synthesize(
        self,
        utterance: Utterance,
        *,
        voice: str | None = None,
        rate: float = 1.0,
    ) -> SynthesizedSpan:
        if not self.api_key:
            raise ProviderError(
                "ElevenLabs API key is missing. Set ELEVENLABS_API_KEY in .env or keyring."
            )

        voice_id = voice or "21m00Tcm4TlvDq8ikWAM"  # Rachel default
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": utterance.spoken_text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 429:
                raise ProviderError("ElevenLabs rate limit exceeded (429)", retryable=True)
            if resp.status_code != 200:
                raise ProviderError(
                    f"ElevenLabs synthesis failed ({resp.status_code}): {resp.text}"
                )

            data = resp.json()
            audio_bytes = base64.b64decode(data["audio_base64"])
            alignment = data.get("alignment", {})

        out_path = self.cache_dir / f"{utterance.utterance_id.replace(':', '_')}.mp3"
        out_path.write_bytes(audio_bytes)

        # Parse character alignments into WordTimings
        alignment.get("characters", [])
        start_times = alignment.get("character_start_times_seconds", [])
        end_times = alignment.get("character_end_times_seconds", [])

        word_timings: list[WordTiming] = []
        words = utterance.spoken_text.split()
        char_idx = 0

        for w in words:
            w_start = utterance.spoken_text.find(w, char_idx)
            w_end = w_start + len(w) if w_start != -1 else char_idx + len(w)
            char_idx = w_end

            s_sec = (
                start_times[w_start]
                if w_start < len(start_times)
                else (start_times[-1] if start_times else 0.0)
            )
            e_sec = (
                end_times[w_end - 1]
                if w_end - 1 < len(end_times)
                else (end_times[-1] if end_times else s_sec + 0.3)
            )

            word_timings.append(
                WordTiming(
                    word=w,
                    char_start=w_start,
                    char_end=w_end,
                    start_sec=round(s_sec, 3),
                    end_sec=round(e_sec, 3),
                )
            )

        dur_sec = end_times[-1] if end_times else 1.0

        return SynthesizedSpan(
            utterance_id=utterance.utterance_id,
            audio_path=out_path,
            duration_sec=round(dur_sec, 3),
            pause_after_sec=utterance.pause_after_ms / 1000.0,
            word_timings=tuple(word_timings),
            provider=self.name,
            voice=voice_id,
        )
