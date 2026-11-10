import logging
import re
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from cantoleaf import __version__
from cantoleaf.config import get_settings
from cantoleaf.export.m4b import master_m4b_audiobook
from cantoleaf.export.vault import export_obsidian_marginalia
from cantoleaf.ingest.registry import load_document
from cantoleaf.models import (
    BlockKind,
    BookMetadata,
    DepthGear,
    LangMode,
    SynthesizedSpan,
    Utterance,
)
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
SAFE_AUDIO_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+\.(mp3|wav|m4a|ogg)$")

_shared_tracker: UsageTracker | None = None


def get_shared_tracker() -> UsageTracker:
    global _shared_tracker
    if _shared_tracker is None:
        settings = get_settings()
        _shared_tracker = UsageTracker(max_budget_usd=settings.cantoleaf_max_cost_usd)
    return _shared_tracker


def _get_allowed_roots() -> list[Path]:
    settings = get_settings()
    roots = [
        Path.cwd().resolve(),
        (Path.home() / ".cantoleaf").resolve(),
        settings.cantoleaf_cache_dir.resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]
    return roots


def _validate_document_path(raw_path: str) -> Path:
    """Validates that the path is a safe, existing document file within allowed roots."""
    if not raw_path or ".." in raw_path:
        raise HTTPException(status_code=400, detail="Invalid document path format.")

    path = Path(raw_path).expanduser().resolve()
    allowed_roots = _get_allowed_roots()
    if not any(path.is_relative_to(root) for root in allowed_roots):
        raise HTTPException(
            status_code=403,
            detail="Access denied: document path must be within the project directory or ~/.cantoleaf.",
        )

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

    # 3. Synthesize via pipeline with cache & budget protection using shared tracker
    cache = AudioCache()
    tracker = get_shared_tracker()
    pipeline = SynthesisPipeline(tts, cache, tracker)

    results: list[dict[str, object]] = []
    for u in utterances:
        span = await pipeline.synthesize_utterance(u, voice=req.voice, rate=req.rate)
        results.append(
            {
                "utterance_id": span.utterance_id,
                "block_index": u.block_index,
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
    if not SAFE_AUDIO_FILENAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid audio filename format.")

    settings = get_settings()
    cache_root = settings.cantoleaf_cache_dir.resolve()
    found_file: Path | None = None

    # Search provider subdirectories inside cache dir without allowing glob syntax
    for p in cache_root.glob(f"**/{filename}"):
        if p.is_file() and p.name == filename:
            found_file = p.resolve()
            break

    if not found_file or not found_file.exists() or not found_file.is_relative_to(cache_root):
        raise HTTPException(status_code=404, detail="Audio file not found in cache.")

    media_type = "audio/mpeg" if found_file.suffix.lower() == ".mp3" else "audio/wav"
    return FileResponse(found_file, media_type=media_type)


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
    tracker = get_shared_tracker()
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

    allowed_roots = _get_allowed_roots()
    if req.out_path:
        candidate_out = Path(req.out_path).expanduser().resolve()
        if not any(candidate_out.is_relative_to(root) for root in allowed_roots):
            raise HTTPException(
                status_code=403,
                detail="Access denied: out_path must be within working directory or ~/.cantoleaf.",
            )
        out_file = candidate_out
    else:
        out_file = (Path.cwd() / f"{safe_path.stem}_{gear.value}.m4b").resolve()

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


class CrystallizeRequest(BaseModel):
    book_title: str
    author: str = "Unknown"
    chapter_title: str
    source_text: str
    block_index: int = 0
    vault_dir: str = "./notes"


@app.post("/api/chapter/crystallize")
async def crystallize_note(req: CrystallizeRequest) -> dict[str, str]:
    u = Utterance(
        utterance_id=f"crystallize:{req.block_index}",
        chapter_index=0,
        block_index=req.block_index,
        gear=DepthGear.VERBATIM,
        lang_mode=LangMode.SOURCE,
        block_kind=BlockKind.QUOTE,
        source_text=req.source_text,
        spoken_text=req.source_text,
    )

    allowed_roots = _get_allowed_roots()
    v_dir = Path(req.vault_dir).expanduser().resolve()
    if not any(v_dir.is_relative_to(root) for root in allowed_roots):
        v_dir = (Path.cwd() / "notes").resolve()

    saved_path = export_obsidian_marginalia(
        req.book_title, req.author, req.chapter_title, [u], v_dir
    )
    return {"status": "saved", "path": str(saved_path)}
