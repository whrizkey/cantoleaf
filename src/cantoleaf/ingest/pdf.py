import re
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF

from cantoleaf.errors import IngestError
from cantoleaf.ingest.classifier import classify_block
from cantoleaf.ingest.cleaner import clean_text
from cantoleaf.models import BookMetadata, Chapter, SemanticBlock

HEADING_REGEX = re.compile(
    r"^(?:(?:chapter|part|section)\s+(?:[0-9]+|[ivxlcdm]+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b(?:\s*[:.\-—]|\s+[A-Z]|\s*$)|prologue\b|epilogue\b|introduction\b|conclusion\b)",
    re.IGNORECASE,
)
PAGE_NUM_REGEX = re.compile(
    r"^(?:page\s+)?(?:[0-9]+|[ivxlcdm]+)(?:\s+of\s+[0-9]+)?$", re.IGNORECASE
)


def _is_probable_heading(line: str) -> bool:
    cleaned = line.strip()
    if len(cleaned) > 75 or len(cleaned) < 3:
        return False
    if not HEADING_REGEX.match(cleaned):
        return False
    # Disqualify prose sentences that happen to mention a chapter/section
    lower = f" {cleaned.lower()} "
    narrative_markers = (
        " shows ",
        " describes ",
        " illustrates ",
        " explains ",
        " is ",
        " was ",
        " were ",
        " had ",
        " of ",
    )
    return not any(m in lower for m in narrative_markers)


def parse_pdf(file_path: Path) -> BookMetadata:
    """
    Parses a PDF using geometric bounding boxes to strip running headers and footers
    (repeating elements in top/bottom 7% of page height), image blocks, and page numbers.
    """
    try:
        doc = fitz.open(str(file_path))
    except Exception as e:
        raise IngestError(f"Failed to open PDF file at {file_path}: {e}") from e

    try:
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
                # Filter out image blocks (block_type != 0)
                if len(b) > 6 and b[6] != 0:
                    continue
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
            blocks = page.get_text("blocks")
            for b in blocks:
                # Filter out image blocks (block_type != 0)
                if len(b) > 6 and b[6] != 0:
                    continue

                text = b[4].strip()
                if not text or text in ignored_headers_footers:
                    continue

                # Filter out standalone page numbers
                if PAGE_NUM_REGEX.match(text):
                    continue

                cleaned = clean_text(text)
                if not cleaned:
                    continue

                # Check if first line of block is a heading (e.g. "Chapter 1\nContent...")
                lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
                sub_blocks: list[tuple[str, bool]] = []
                if lines and len(lines) > 1 and _is_probable_heading(lines[0]):
                    sub_blocks.append((lines[0], True))
                    rest = " ".join(lines[1:]).strip()
                    if rest:
                        sub_blocks.append((rest, False))
                else:
                    is_h = _is_probable_heading(cleaned)
                    sub_blocks.append((cleaned, is_h))

                for sub_text, is_heading in sub_blocks:
                    sub_cleaned = clean_text(sub_text)
                    if not sub_cleaned:
                        continue

                    if is_heading:
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
                            ch_idx += 1
                            current_blocks = []
                        current_title = sub_cleaned

                    kind = classify_block(sub_cleaned, is_heading=is_heading)
                    current_blocks.append(
                        SemanticBlock(
                            block_index=blk_idx,
                            kind=kind,
                            text=sub_cleaned,
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
    finally:
        doc.close()
