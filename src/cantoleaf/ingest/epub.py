import re
from pathlib import Path

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from cantoleaf.errors import IngestError
from cantoleaf.ingest.classifier import classify_block
from cantoleaf.ingest.cleaner import clean_text
from cantoleaf.models import BookMetadata, Chapter, SemanticBlock


def parse_epub(file_path: Path) -> BookMetadata:
    """
    Parses an EPUB 2/3 file following book.spine order, extracting clean text
    with space separators (preventing 'Hellobigworld') and skipping duplicate nested tags.
    """
    try:
        book = epub.read_epub(str(file_path), options={"ignore_ncx": False})
    except Exception as e:
        raise IngestError(f"Failed to read EPUB file at {file_path}: {e}") from e

    title_entries = book.get_metadata("DC", "title")
    title = title_entries[0][0] if title_entries else file_path.stem
    author_entries = book.get_metadata("DC", "creator")
    author = author_entries[0][0] if author_entries else "Unknown Author"
    lang_entries = book.get_metadata("DC", "language")
    language = lang_entries[0][0] if lang_entries else "en"

    chapters: list[Chapter] = []
    ch_idx = 0

    # Extract cover art image if present
    cover_image_path: Path | None = None
    for it in book.get_items():
        if it.get_type() in (ebooklib.ITEM_COVER, ebooklib.ITEM_IMAGE):
            it_name = it.get_name().lower() if hasattr(it, "get_name") else ""
            if "cover" in it_name or it.get_type() == ebooklib.ITEM_COVER:
                covers_dir = Path("/tmp/cantoleaf_covers")
                covers_dir.mkdir(parents=True, exist_ok=True)
                cover_image_path = covers_dir / f"{file_path.stem}_cover.jpg"
                try:
                    raw_cover = it.get_content()
                    cover_bytes = (
                        raw_cover.encode("utf-8") if isinstance(raw_cover, str) else raw_cover
                    )
                    cover_image_path.write_bytes(cover_bytes)
                except Exception:
                    cover_image_path = None
                break

    # Follow spine order for correct linear reading sequence
    spine_ids = [item[0] for item in book.spine]
    spine_items = []
    for item_id in spine_ids:
        item = book.get_item_with_id(item_id)
        if item:
            spine_items.append(item)

    if not spine_items:
        spine_items = list(book.get_items())

    for item in spine_items:
        # Only process document items
        if hasattr(item, "get_type") and item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue

        item_name = item.get_name().lower() if hasattr(item, "get_name") else ""
        # Skip standalone navigation documents or covers using word boundaries (prevent dropping 'discovery' or 'stock')
        if re.search(r"\b(nav|toc|cover|titlepage)\b", item_name):
            continue

        raw_content = item.get_content()
        content = (
            raw_content.decode("utf-8", errors="replace")
            if isinstance(raw_content, bytes)
            else raw_content
        )
        soup = BeautifulSoup(content, "lxml" if True else "html.parser")

        # Extract chapter title if any header exists
        h_tag = soup.find(["h1", "h2", "h3"])
        ch_title = h_tag.get_text(separator=" ", strip=True) if h_tag else f"Chapter {ch_idx + 1}"

        blocks: list[SemanticBlock] = []
        blk_idx = 0

        # Select top-level content elements, ensuring nested tags are not duplicated
        target_tags = [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "blockquote",
            "aside",
            "li",
            "pre",
            "table",
        ]
        for element in soup.find_all(target_tags):
            # Skip child elements inside blockquote, aside, or table to prevent duplicate text
            if element.name in ("p", "li", "pre") and (
                element.find_parent("blockquote")
                or element.find_parent("aside")
                or element.find_parent("table")
            ):
                continue
            if element.name == "li" and element.find_parent("li"):
                continue

            raw_text = element.get_text(separator=" ", strip=True)
            if not raw_text:
                continue

            cleaned = clean_text(raw_text)
            if not cleaned:
                continue

            is_heading = element.name in ("h1", "h2", "h3", "h4", "h5", "h6")
            is_quote = element.name == "blockquote"
            elem_classes = element.get("class", [])
            if isinstance(elem_classes, str):
                elem_classes = [elem_classes]
            is_footnote = (
                element.name == "aside"
                or any("footnote" in c.lower() for c in elem_classes)
                or element.get("epub:type") == "footnote"
            )
            kind = classify_block(
                cleaned,
                is_heading=is_heading,
                is_quote=is_quote,
                is_footnote=is_footnote,
            )

            blocks.append(
                SemanticBlock(
                    block_index=blk_idx,
                    kind=kind,
                    text=cleaned,
                )
            )
            blk_idx += 1

        if blocks:
            est_chars = sum(len(b.text) for b in blocks)
            chapters.append(
                Chapter(
                    index=ch_idx,
                    title=ch_title,
                    blocks=tuple(blocks),
                    estimated_chars=est_chars,
                )
            )
            ch_idx += 1

    if not chapters:
        raise IngestError(f"No readable chapter text found in {file_path}")

    return BookMetadata(
        book_id=file_path.stem.lower().replace(" ", "_"),
        title=str(title),
        author=str(author),
        language=str(language),
        chapters=tuple(chapters),
        cover_image=cover_image_path,
    )
