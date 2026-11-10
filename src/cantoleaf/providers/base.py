from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from cantoleaf.models import DepthGear, LangMode, SynthesizedSpan, Utterance


@dataclass(frozen=True)
class Voice:
    voice_id: str
    name: str
    language: str
    gender: str = "neutral"
    provider: str = ""


@runtime_checkable
class TtsProvider(Protocol):
    """Protocol for local and BYOK Text-To-Speech speech engines."""

    name: str
    sample_rate: int

    async def list_voices(self, language: str = "en") -> list[Voice]:
        """Lists available voices for the specified language."""
        ...

    async def synthesize(
        self,
        utterance: Utterance,
        *,
        voice: str | None = None,
        rate: float = 1.0,
    ) -> SynthesizedSpan:
        """Synthesizes an utterance into audio with word timings."""
        ...


@runtime_checkable
class AdaptProvider(Protocol):
    """Protocol for LLM and local extractive adapters (summarization, translation, Q&A)."""

    name: str

    async def adapt_depth(
        self,
        text: str,
        target_gear: DepthGear,
        *,
        context: list[str] | None = None,
    ) -> str:
        """Adapts a chapter/paragraph into the target depth gear (Pulse / Crux / Unpack)."""
        ...

    async def translate(
        self,
        text: str,
        target_lang: str,
        lang_mode: LangMode = LangMode.TARGET,
        *,
        context: list[str] | None = None,
    ) -> str:
        """Translates text according to the selected LangMode."""
        ...

    async def generate_recall_questions(
        self,
        chapter_title: str,
        chapter_summary: str,
    ) -> list[tuple[str, str]]:
        """Generates 2-3 Socratic question/answer pairs for Memory Locks."""
        ...
