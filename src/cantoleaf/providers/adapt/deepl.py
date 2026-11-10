import httpx

from cantoleaf.errors import ProviderError
from cantoleaf.ingest.segmenter import split_into_sentences
from cantoleaf.models import DepthGear, LangMode
from cantoleaf.providers.base import AdaptProvider


class DeeplAdaptProvider(AdaptProvider):
    """
    DeepL API translation adapter.
    """

    name: str = "deepl"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        # Free API keys end with ':fx'
        self.endpoint = (
            "https://api-free.deepl.com/v2/translate"
            if api_key.endswith(":fx")
            else "https://api.deepl.com/v2/translate"
        )

    async def adapt_depth(
        self,
        text: str,
        target_gear: DepthGear,
        *,
        context: list[str] | None = None,
    ) -> str:
        # Heuristic fallback for non-LLM DeepL
        sentences = split_into_sentences(text)
        if not sentences:
            return ""
        if target_gear == DepthGear.PULSE:
            return sentences[0]
        if target_gear == DepthGear.CRUX:
            return f"{sentences[0]} {sentences[-1]}" if len(sentences) > 2 else text
        return text

    async def translate(
        self,
        text: str,
        target_lang: str,
        lang_mode: LangMode = LangMode.TARGET,
        *,
        context: list[str] | None = None,
    ) -> str:
        if lang_mode == LangMode.SOURCE:
            return text
        if not self.api_key:
            raise ProviderError("DeepL API key is missing. Set DEEPL_API_KEY in .env or keyring.")

        # DeepL target language code (uppercase, e.g. ID, ES, DE, JA)
        clean_target = target_lang.upper().split("-")[0]
        headers = {
            "Authorization": f"DeepL-Auth-Key {self.api_key}",
        }
        data = {
            "text": [text],
            "target_lang": clean_target,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self.endpoint, headers=headers, data=data)
                if resp.status_code == 429:
                    raise ProviderError("DeepL rate limit exceeded (429)", retryable=True)
                if resp.status_code != 200:
                    raise ProviderError(
                        f"DeepL translation failed ({resp.status_code}): {resp.text}"
                    )
                res_data = resp.json()
                translations = res_data.get("translations", [])
                if translations:
                    return str(translations[0].get("text", text))
                return text
        except httpx.HTTPError as e:
            raise ProviderError(f"DeepL network error: {e}", retryable=True) from e

    async def generate_recall_questions(
        self,
        chapter_title: str,
        chapter_summary: str,
    ) -> list[tuple[str, str]]:
        return [
            (
                f"What is the central premise of {chapter_title}?",
                f"The core thesis establishes that {chapter_summary[:120]}...",
            )
        ]
