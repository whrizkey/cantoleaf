import json

import httpx

from cantoleaf.errors import ProviderError
from cantoleaf.models import DepthGear, LangMode
from cantoleaf.providers.base import AdaptProvider


class OpenAiCompatAdaptProvider(AdaptProvider):
    """
    OpenAI-compatible LLM adapter for Depth Adaptation and Translation.
    Supports official OpenAI, OpenRouter, Groq, and local Ollama/vLLM endpoints.
    """

    name: str = "openai_compat"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model or "gpt-4o-mini"

    async def _chat(self, system_prompt: str, user_prompt: str) -> str:
        if (
            not self.api_key
            and "localhost" not in self.base_url
            and "127.0.0.1" not in self.base_url
        ):
            raise ProviderError("OpenAI API key is missing. Set OPENAI_API_KEY in .env or keyring.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 429:
                    raise ProviderError("OpenAI LLM rate limit exceeded (429)", retryable=True)
                if resp.status_code != 200:
                    raise ProviderError(f"OpenAI LLM call failed ({resp.status_code}): {resp.text}")
                data = resp.json()
                choice = data.get("choices", [{}])[0]
                content = str(choice.get("message", {}).get("content", "")).strip()
                return content
        except httpx.HTTPError as e:
            raise ProviderError(
                f"OpenAI network error during LLM completion: {e}", retryable=True
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
            sys_msg = "You are an executive audio summarizer. Condense the text into a single crisp topic sentence conveying the core thesis."
        elif target_gear == DepthGear.CRUX:
            sys_msg = "You are an audio editor. Keep core reasoning intact while concisely bridging anecdotes into one bracketed sentence."
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
                f"Translate the following text into fluent {target_lang}. "
                "Preserve key technical, scientific, or domain terminology in their original English form."
            )
        else:
            sys_msg = (
                f"Translate the following spoken audiobook passage into natural, idiomatic {target_lang}. "
                "Do not add any meta-commentary, markdown formatting, or brackets. Output only the translated sentence."
            )

        res = await self._chat(sys_msg, text)
        return res or text

    async def generate_recall_questions(
        self,
        chapter_title: str,
        chapter_summary: str,
    ) -> list[tuple[str, str]]:
        sys_msg = (
            "You create Socratic Active Recall retrieval questions for audiobooks. "
            "Respond ONLY with a JSON list of objects having 'question' and 'answer' keys. No code fencing."
        )
        user_prompt = f"Chapter: {chapter_title}\nSummary: {chapter_summary}"
        raw = await self._chat(sys_msg, user_prompt)
        try:
            items = json.loads(raw)
            pairs: list[tuple[str, str]] = []
            for item in items:
                if "question" in item and "answer" in item:
                    pairs.append((item["question"], item["answer"]))
            return pairs or [
                (f"What is the key takeaway of {chapter_title}?", chapter_summary[:120])
            ]
        except Exception:
            return [(f"What is the key insight of {chapter_title}?", chapter_summary[:120])]
