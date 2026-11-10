from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF

from cantoleaf.errors import IngestError
from cantoleaf.ingest.classifier import classify_block
from cantoleaf.ingest.cleaner import clean_text
from cantoleaf.models import BookMetadata, Chapter, SemanticBlock


def parse_pdf(file_path: Path) -> BookMetadata:
    """
    Parses a PDF using geometric bounding boxes to strip running headers and footers
    (repeating elements in top/bottom 7% of page height).
    """
    try:
        doc = fitz.open(str(file_path))
    except Exception as e:
        raise IngestError(f"Failed to open PDF file at {file_path}: {e}") from e

    metadata = doc.metadata or {}
    title = metadata.get("title") or file_path.stem
    author = metadata.get("author") or "Unknown Author"

    # Pass 1: Collect text blocks with their relative vertical position to detect repeating headers/footers
    header_footer_candidates: Counter[str] = Counter()
    total_pages = len(doc)

    for page in doc:
        page_h = page.rect.height
        top_zone = page_h * 0.07
        bottom_zone = page_h * 0.93
        blocks = page.get_text("blocks")
        for b in blocks:
            # b: (x0, y0, x1, y1, text, block_no, block_type)
            y0, y1, text = b[1], b[3], b[4].strip()
            if not text:
                continue
            if y0 <= top_zone or y1 >= bottom_zone:
                header_footer_candidates[text] += 1

    # Repeating threshold: text appearing in header/footer zone across 3+ pages (or >50% of short docs)
    threshold = max(2, min(3, total_pages // 2))
    ignored_headers_footers = {
        txt for txt, count in header_footer_candidates.items() if count >= threshold
    }

    # Pass 2: Extract semantic blocks
    chapters: list[Chapter] = []
    current_blocks: list[SemanticBlock] = []
    blk_idx = 0
    ch_idx = 0
    current_title = "Chapter 1"

    for _page_idx, page in enumerate(doc):
        page_h = page.rect.height
        blocks = page.get_text("blocks")
        for b in blocks:
            text = b[4].strip()
            if not text or text in ignored_headers_footers:
                continue

            cleaned = clean_text(text)
            if not cleaned:
                continue

            # Detect chapter heading heuristic (short, starts with Chapter, etc.)
            is_heading = len(cleaned) < 80 and any(
                cleaned.lower().startswith(p)
                for p in ("chapter ", "section ", "part ", "prologue", "epilogue")
            )

            if is_heading and current_blocks:
                est_chars = sum(len(x.text) for x in current_blocks)
                chapters.append(
                    Chapter(
                        index=ch_idx,
                        title=current_title,
                        blocks=tuple(current_blocks),
                        estimated_chars=est_chars,
                    )
                )
                ch_idx += 1
                current_blocks = []
                current_title = cleaned

            kind = classify_block(cleaned, is_heading=is_heading)
            current_blocks.append(
                SemanticBlock(
                    block_index=blk_idx,
                    kind=kind,
                    text=cleaned,
                )
            )
            blk_idx += 1

    if current_blocks:
        est_chars = sum(len(x.text) for x in current_blocks)
        chapters.append(
            Chapter(
                index=ch_idx,
                title=current_title,
                blocks=tuple(current_blocks),
                estimated_chars=est_chars,
            )
        )

    if not chapters:
        raise IngestError(f"No extractable text found in PDF {file_path}")

    return BookMetadata(
        book_id=file_path.stem.lower().replace(" ", "_"),
        title=str(title),
        author=str(author),
        language="en",
        chapters=tuple(chapters),
    )
