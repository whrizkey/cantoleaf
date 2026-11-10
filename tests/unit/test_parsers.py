from pathlib import Path

import fitz

from cantoleaf.ingest.docx_md import parse_markdown_or_txt
from cantoleaf.ingest.pdf import parse_pdf


def test_markdown_parser(tmp_path: Path) -> None:
    md_file = tmp_path / "test.md"
    md_file.write_text(
        """# Introduction
This is the opening argument of the book.

## Background
In 1995, an interesting event happened for instance when systems changed.

| Column 1 | Column 2 |
| --- | --- |
| Data A | Data B |
""",
        encoding="utf-8",
    )

    book = parse_markdown_or_txt(md_file)
    assert book.title == "Test"
    assert len(book.chapters) == 2
    assert book.chapters[0].title == "Introduction"
    assert book.chapters[1].title == "Background"
    assert book.chapters[1].blocks[1].kind.value == "anecdote"
    assert book.chapters[1].blocks[2].kind.value == "table"


def test_pdf_header_footer_stripping(tmp_path: Path) -> None:
    pdf_path = tmp_path / "test_book.pdf"
    doc = fitz.open()

    for i in range(5):
        page = doc.new_page(width=600, height=800)
        # Add running header in top 5%
        page.insert_text((50, 30), "CANTOLEAF RESEARCH REPORT", fontsize=10)
        # Add main text body
        page.insert_text(
            (50, 200),
            f"Chapter {i + 1}\nThis is the important core content of page {i + 1}.",
            fontsize=12,
        )
        # Add running page footer in bottom 5%
        page.insert_text((280, 770), f"Page {i + 1} of 5", fontsize=10)

    doc.save(str(pdf_path))
    doc.close()

    book = parse_pdf(pdf_path)
    all_text = " ".join(b.text for ch in book.chapters for b in ch.blocks)

    # Repeating header and footer should be stripped
    assert "CANTOLEAF RESEARCH REPORT" not in all_text
    assert "core content of page" in all_text
