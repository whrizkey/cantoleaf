import httpx

from cantoleaf.errors import ProviderError
from cantoleaf.models import DepthGear, LangMode
from cantoleaf.providers.base import AdaptProvider


class AnthropicAdaptProvider(AdaptProvider):
    """
    Anthropic Claude adapter for Depth Adaptation and Translation.
    Calls Anthropic's official /v1/messages API with anthropic-version header.
    """

    name: str = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-haiku-20241022",
    ) -> None:
        self.api_key = api_key
        self.model = model or "claude-3-5-haiku-20241022"

    async def _chat(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise ProviderError(
                "Anthropic API key is missing. Set ANTHROPIC_API_KEY in .env or keyring."
            )

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 429:
                    raise ProviderError("Anthropic rate limit exceeded (429)", retryable=True)
                if resp.status_code != 200:
                    raise ProviderError(f"Anthropic call failed ({resp.status_code}): {resp.text}")
                data = resp.json()
                content_blocks = data.get("content", [])
                text_parts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
                return "".join(text_parts).strip()
        except httpx.HTTPError as e:
            raise ProviderError(
                f"Anthropic network error during message completion: {e}", retryable=True
            ) from e

    async def adapt_depth(
        self,
        text: str,
        target_gear: DepthGear,
        *,
        context: list[str] | None = None,
    ) -> str:
        if target_gear == DepthGear.VERBATIM:
            return text

        if target_gear == DepthGear.PULSE:
            sys_msg = (
                "You are an executive audio summarizer. Condense the text into a single crisp topic "
                "sentence conveying the core thesis."
            )
        elif target_gear == DepthGear.CRUX:
            sys_msg = (
                "You are an audio editor. Keep core reasoning intact while concisely bridging "
                "anecdotes into one bracketed sentence."
            )
        else:
            sys_msg = "Explain this passage in intuitive everyday terms using a vivid analogy."

        res = await self._chat(sys_msg, text)
        return res or text

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

        if lang_mode == LangMode.CODE_SWITCH:
            sys_msg = (
                f"Translate this text into {target_lang}, but keep domain terminology, "
                "brand names, and code tokens in their original English/source form."
            )
        else:
            sys_msg = (
                f"Translate the following text into fluent, natural {target_lang} for spoken audio narration. "
                "Output only the translated sentence."
            )

        res = await self._chat(sys_msg, text)
        return res or text

    async def generate_recall_questions(
        self,
        chapter_title: str,
        chapter_summary: str,
    ) -> list[tuple[str, str]]:
        import json

        sys_msg = (
            "You create Socratic Active Recall retrieval questions for audiobooks. "
            "Respond ONLY with a JSON list of objects having 'question' and 'answer' keys. No markdown code blocks."
        )
        user_prompt = f"Chapter: {chapter_title}\nSummary: {chapter_summary}"
        raw = await self._chat(sys_msg, user_prompt)
        try:
            items = json.loads(raw)
            pairs: list[tuple[str, str]] = []
            for item in items:
                if "question" in item and "answer" in item:
                    pairs.append((str(item["question"]), str(item["answer"])))
            return pairs or [
                (f"What is the key takeaway of {chapter_title}?", chapter_summary[:120])
            ]
        except Exception:
            return [(f"What is the key insight of {chapter_title}?", chapter_summary[:120])]
