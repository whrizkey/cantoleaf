from pathlib import Path

from cantoleaf.errors import IngestError
from cantoleaf.ingest.docx_md import parse_docx, parse_markdown_or_txt
from cantoleaf.ingest.epub import parse_epub
from cantoleaf.ingest.pdf import parse_pdf
from cantoleaf.models import BookMetadata


def load_document(source: str | Path) -> BookMetadata:
    """Dispatches document parsing based on file extension or source type."""
    path = Path(source)
    if not path.exists():
        raise IngestError(f"File not found: {source}")

    suffix = path.suffix.lower()
    if suffix in (".epub",):
        return parse_epub(path)
    if suffix in (".pdf",):
        return parse_pdf(path)
    if suffix in (".docx",):
        return parse_docx(path)
    if suffix in (".md", ".markdown", ".txt"):
        return parse_markdown_or_txt(path)

    raise IngestError(f"Unsupported format: {suffix}. Supported: .epub, .pdf, .docx, .md, .txt")
