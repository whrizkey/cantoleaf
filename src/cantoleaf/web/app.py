from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from cantoleaf import __version__
from cantoleaf.ingest.registry import load_document
from cantoleaf.models import BookMetadata

app = FastAPI(title="CantoLeaf Studio", version=__version__)
static_dir = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
async def serve_index() -> HTMLResponse:
    index_file = static_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index template missing")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get("/api/book/inspect")
async def inspect_book(path: str) -> dict[str, object]:
    try:
        book: BookMetadata = load_document(path)
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
        raise HTTPException(status_code=400, detail=str(e)) from e
