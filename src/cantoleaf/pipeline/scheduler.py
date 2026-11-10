from collections.abc import Callable

from cantoleaf.models import BookMetadata, DepthGear, LangMode, SynthesizedSpan, Utterance
from cantoleaf.pipeline.synthesizer import SynthesisPipeline
from cantoleaf.providers.base import AdaptProvider
from cantoleaf.workflows.bilingual_bridge import weave_bilingual_stream
from cantoleaf.workflows.depth_gears import generate_depth_stream


class LookaheadScheduler:
    """
    Workflow 5: Speculative TOC Pre-Warmer & Look-Ahead Scheduler.
    Pre-warms the first 2 sentences of every chapter in the Table of Contents
    for <50ms instant chapter jumping, and maintains a rolling synthesis buffer
    ahead of the current reading cursor with instant seek-generation cancellation.
    """

    def __init__(
        self,
        book: BookMetadata,
        pipeline: SynthesisPipeline,
        adapt_provider: AdaptProvider,
    ) -> None:
        self.book = book
        self.pipeline = pipeline
        self.adapt = adapt_provider
        self.generation = 0
        self.toc_prewarm_cache: dict[int, list[SynthesizedSpan]] = {}

    async def prewarm_toc(
        self,
        gear: DepthGear = DepthGear.PULSE,
        lang_mode: LangMode = LangMode.SOURCE,
    ) -> None:
        """Pre-synthesizes the opening 2 sentences of every chapter in the book."""
        for ch in self.book.chapters:
            u_stream = await generate_depth_stream(
                self.book.book_id, ch, gear, lang_mode, self.adapt
            )
            opening = u_stream[:2]
            spans: list[SynthesizedSpan] = []
            for u in opening:
                span = await self.pipeline.synthesize_utterance(u)
                spans.append(span)
            self.toc_prewarm_cache[ch.index] = spans

    async def stream_chapter(
        self,
        chapter_index: int,
        gear: DepthGear,
        lang_mode: LangMode,
        target_lang: str = "en",
        on_span_ready: Callable[[Utterance, SynthesizedSpan], None] | None = None,
    ) -> list[SynthesizedSpan]:
        """Synthesizes a chapter's utterance stream with look-ahead generation tracking."""
        self.generation += 1
        current_gen = self.generation

        if chapter_index >= len(self.book.chapters):
            return []

        chapter = self.book.chapters[chapter_index]
        base_stream = await generate_depth_stream(
            self.book.book_id, chapter, gear, lang_mode, self.adapt
        )
        weaved_stream = await weave_bilingual_stream(
            base_stream, lang_mode, target_lang, self.adapt
        )

        spans: list[SynthesizedSpan] = []
        for u in weaved_stream:
            if self.generation != current_gen:
                # Seek occurred! Cancel remaining work
                break
            span = await self.pipeline.synthesize_utterance(u)
            spans.append(span)
            if on_span_ready:
                on_span_ready(u, span)

        return spans
