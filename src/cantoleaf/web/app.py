import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from cantoleaf import __version__
from cantoleaf.config import get_settings
from cantoleaf.export.m4b import master_m4b_audiobook
from cantoleaf.ingest.registry import load_document
from cantoleaf.models import BookMetadata, DepthGear, LangMode, SynthesizedSpan
from cantoleaf.pipeline.accounting import UsageTracker
from cantoleaf.pipeline.cache import AudioCache
from cantoleaf.pipeline.synthesizer import SynthesisPipeline
from cantoleaf.providers.registry import get_adapt_provider, get_tts_provider
from cantoleaf.workflows.bilingual_bridge import weave_bilingual_stream
from cantoleaf.workflows.depth_gears import generate_depth_stream

logger = logging.getLogger("cantoleaf.web")
app = FastAPI(title="CantoLeaf Studio", version=__version__)
static_dir = Path(__file__).parent / "static"

ALLOWED_EXTENSIONS = {".epub", ".pdf", ".docx", ".md", ".markdown", ".txt"}


def _validate_document_path(raw_path: str) -> Path:
    """Validates that the path is a safe, existing document file."""
    if not raw_path or ".." in raw_path:
        raise HTTPException(status_code=400, detail="Invalid document path format.")

    path = Path(raw_path).expanduser().resolve()
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format {path.suffix}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    if not path.is_file() or not path.exists():
        raise HTTPException(status_code=404, detail="Document file not found.")

    return path


class SynthesizeRequest(BaseModel):
    path: str
    chapter_index: int = 0
    gear: str = "verbatim"
    lang_mode: str = "source"
    target_lang: str = "en"
    provider: str = "edge"
    voice: str | None = None
    rate: float = 1.0


class ExportRequest(BaseModel):
    path: str
    out_path: str | None = None
    gear: str = "verbatim"
    provider: str = "edge"
    voice: str | None = None


@app.get("/", response_class=HTMLResponse)
async def serve_index() -> HTMLResponse:
    index_file = static_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index template missing")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get("/api/book/inspect")
async def inspect_book(path: str) -> dict[str, object]:
    safe_path = _validate_document_path(path)
    try:
        book: BookMetadata = load_document(safe_path)
        return {
            "title": book.title,
            "author": book.author,
            "language": book.language,
            "chapters": [
                {
                    "index": ch.index,
                    "title": ch.title,
                    "estimated_chars": ch.estimated_chars,
                    "block_count": len(ch.blocks),
                }
                for ch in book.chapters
            ],
        }
    except Exception as e:
        logger.error("Failed to inspect book: %s", e)
        raise HTTPException(status_code=400, detail="Failed to parse document structure.") from e


@app.post("/api/chapter/synthesize")
async def synthesize_chapter(req: SynthesizeRequest) -> dict[str, object]:
    safe_path = _validate_document_path(req.path)
    book = load_document(safe_path)

    if req.chapter_index < 0 or req.chapter_index >= len(book.chapters):
        raise HTTPException(status_code=400, detail="Invalid chapter index.")

    chapter = book.chapters[req.chapter_index]
    gear = (
        DepthGear(req.gear.lower())
        if req.gear.lower() in DepthGear._value2member_map_
        else DepthGear.VERBATIM
    )
    lang_mode = (
        LangMode(req.lang_mode.lower())
        if req.lang_mode.lower() in LangMode._value2member_map_
        else LangMode.SOURCE
    )

    settings = get_settings()
    tts_name = req.provider or settings.cantoleaf_tts_provider.value
    tts = get_tts_provider(tts_name)
    adapt = get_adapt_provider(settings.cantoleaf_adapt_provider.value)

    # 1. Generate depth stream
    utterances = await generate_depth_stream(book.book_id, chapter, gear, lang_mode, adapt)

    # 2. Weave bilingual stream if applicable
    if lang_mode != LangMode.SOURCE:
        utterances = await weave_bilingual_stream(utterances, lang_mode, req.target_lang, adapt)

    # 3. Synthesize via pipeline with cache & budget protection
    cache = AudioCache()
    tracker = UsageTracker(max_budget_usd=settings.cantoleaf_max_cost_usd)
    pipeline = SynthesisPipeline(tts, cache, tracker)

    results: list[dict[str, object]] = []
    for u in utterances:
        span = await pipeline.synthesize_utterance(u, voice=req.voice, rate=req.rate)
        results.append(
            {
                "utterance_id": span.utterance_id,
                "source_text": u.source_text,
                "spoken_text": u.spoken_text,
                "audio_url": f"/api/audio/{span.audio_path.name}",
                "duration_sec": span.duration_sec,
                "pause_after_sec": span.pause_after_sec,
                "word_timings": [
                    {
                        "word": wt.word,
                        "char_start": wt.char_start,
                        "char_end": wt.char_end,
                        "start_sec": wt.start_sec,
                        "end_sec": wt.end_sec,
                    }
                    for wt in span.word_timings
                ],
            }
        )

    return {
        "chapter_index": req.chapter_index,
        "chapter_title": chapter.title,
        "spans": results,
    }


@app.get("/api/audio/{filename}")
async def serve_audio(filename: str) -> FileResponse:
    settings = get_settings()
    # Search in provider subdirectories inside cache dir
    found_file: Path | None = None
    for p in settings.cantoleaf_cache_dir.rglob(filename):
        if p.is_file():
            found_file = p
            break

    if not found_file or not found_file.exists():
        raise HTTPException(status_code=404, detail="Audio file not found in cache.")

    return FileResponse(found_file, media_type="audio/mpeg")


@app.post("/api/book/export-m4b")
async def export_m4b(req: ExportRequest) -> dict[str, object]:
    safe_path = _validate_document_path(req.path)
    book = load_document(safe_path)
    gear = (
        DepthGear(req.gear.lower())
        if req.gear.lower() in DepthGear._value2member_map_
        else DepthGear.VERBATIM
    )

    settings = get_settings()
    tts = get_tts_provider(req.provider or settings.cantoleaf_tts_provider.value)
    adapt = get_adapt_provider(settings.cantoleaf_adapt_provider.value)
    cache = AudioCache()
    tracker = UsageTracker(max_budget_usd=settings.cantoleaf_max_cost_usd)
    pipeline = SynthesisPipeline(tts, cache, tracker)

    all_spans: list[SynthesizedSpan] = []
    chapter_markers: list[tuple[str, float, float]] = []
    cursor_s = 0.0

    for ch in book.chapters:
        ch_start = cursor_s
        utterances = await generate_depth_stream(book.book_id, ch, gear, LangMode.SOURCE, adapt)
        for u in utterances:
            span = await pipeline.synthesize_utterance(u, voice=req.voice)
            all_spans.append(span)
            cursor_s += span.duration_sec + span.pause_after_sec
        chapter_markers.append((ch.title, ch_start, cursor_s))

    out_file = Path(req.out_path or f"{safe_path.stem}.m4b").resolve()
    mastered = master_m4b_audiobook(
        all_spans,
        chapter_markers,
        out_file,
        book_title=book.title,
        author=book.author,
        cover_image=book.cover_image,
    )

    return {
        "status": "success",
        "out_file": str(mastered),
        "total_duration_sec": round(cursor_s, 2),
    }
