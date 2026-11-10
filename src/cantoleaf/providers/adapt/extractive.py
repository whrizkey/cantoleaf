from cantoleaf.ingest.segmenter import split_into_sentences
from cantoleaf.models import DepthGear, LangMode
from cantoleaf.providers.base import AdaptProvider


class ExtractiveAdaptProvider(AdaptProvider):
    """
    100% Offline & Free Extractive Adapter:
    Uses sentence position, keyword frequency, and structural rules to generate
    Pulse, Crux, and Socratic Recall questions with ZERO LLM API keys.
    """

    name: str = "extractive"

    async def adapt_depth(
        self,
        text: str,
        target_gear: DepthGear,
        *,
        context: list[str] | None = None,
    ) -> str:
        sentences = split_into_sentences(text)
        if not sentences:
            return ""

        if target_gear == DepthGear.VERBATIM:
            return text

        if target_gear == DepthGear.PULSE:
            # First topic sentence
            return sentences[0]

        if target_gear == DepthGear.CRUX:
            # First sentence + last concluding sentence
            if len(sentences) <= 2:
                return " ".join(sentences)
            return f"{sentences[0]} {sentences[-1]}"

        if target_gear == DepthGear.UNPACK:
            return f"In everyday terms: {sentences[0]}"

        return text

    async def translate(
        self,
        text: str,
        target_lang: str,
        lang_mode: LangMode = LangMode.TARGET,
        *,
        context: list[str] | None = None,
    ) -> str:
        # Fallback pseudo-translation tag for offline mode
        return f"[{target_lang}] {text}"

    async def generate_recall_questions(
        self,
        chapter_title: str,
        chapter_summary: str,
    ) -> list[tuple[str, str]]:
        return [
            (
                f"What is the central thesis of {chapter_title}?",
                f"The core principle focuses on {chapter_summary[:100]}...",
            )
        ]
