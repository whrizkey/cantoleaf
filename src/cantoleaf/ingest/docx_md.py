from pathlib import Path

from cantoleaf.errors import IngestError
from cantoleaf.ingest.classifier import classify_block
from cantoleaf.ingest.cleaner import clean_text
from cantoleaf.models import BookMetadata, Chapter, SemanticBlock


def parse_markdown_or_txt(file_path: Path) -> BookMetadata:
    """Parses a Markdown or plain text file into chapters and semantic blocks."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        raise IngestError(f"Failed to read file {file_path}: {e}") from e

    lines = content.split("\n")
    chapters: list[Chapter] = []
    current_blocks: list[SemanticBlock] = []
    current_title = "Chapter 1"
    ch_idx = 0
    blk_idx = 0

    paragraphs: list[str] = []
    curr_para: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if curr_para:
                paragraphs.append("\n".join(curr_para))
                curr_para = []
        elif stripped.startswith("#"):
            if curr_para:
                paragraphs.append("\n".join(curr_para))
                curr_para = []
            paragraphs.append(stripped)
        else:
            curr_para.append(stripped)
    if curr_para:
        paragraphs.append("\n".join(curr_para))

    for p in paragraphs:
        cleaned = clean_text(p)
        if not cleaned:
            continue

        is_heading = cleaned.startswith("# ") or cleaned.startswith("## ")
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
            current_title = cleaned.lstrip("#").strip()

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
        raise IngestError(f"No readable content found in {file_path}")

    return BookMetadata(
        book_id=file_path.stem.lower().replace(" ", "_"),
        title=file_path.stem.replace("_", " ").title(),
        author="Unknown Author",
        language="en",
        chapters=tuple(chapters),
    )


def parse_docx(file_path: Path) -> BookMetadata:
    """Parses a Word .docx document into chapters and semantic blocks."""
    try:
        import docx
    except ImportError as e:
        raise IngestError("python-docx is required to parse .docx files.") from e

    try:
        doc = docx.Document(str(file_path))
    except Exception as e:
        raise IngestError(f"Failed to read DOCX file {file_path}: {e}") from e

    chapters: list[Chapter] = []
    current_blocks: list[SemanticBlock] = []
    current_title = "Chapter 1"
    ch_idx = 0
    blk_idx = 0

    for para in doc.paragraphs:
        cleaned = clean_text(para.text)
        if not cleaned:
            continue

        style_name = para.style.name.lower() if para.style and para.style.name else ""
        is_heading = "heading" in style_name or cleaned.lower().startswith("chapter ")

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
        raise IngestError(f"No readable content found in DOCX file {file_path}")

    core_props = doc.core_properties
    title = (core_props.title if core_props and core_props.title else "") or file_path.stem.replace(
        "_", " "
    ).title()
    author = (core_props.author if core_props and core_props.author else "") or "Unknown Author"

    return BookMetadata(
        book_id=file_path.stem.lower().replace(" ", "_"),
        title=title,
        author=author,
        language="en",
        chapters=tuple(chapters),
    )
