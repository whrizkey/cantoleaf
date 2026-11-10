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
For instance, consider the remarkable case where an interesting event happened when systems changed across the entire department.

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


def test_epub_substring_chapter_names_not_dropped(tmp_path: Path) -> None:
    """Chapters containing 'cover', 'nav', or 'toc' as substrings (e.g. discovery, stock) are preserved."""
    from ebooklib import epub

    from cantoleaf.ingest.epub import parse_epub

    book = epub.EpubBook()
    book.set_identifier("epub_test_disc")
    book.set_title("Exploration and Discovery")
    book.set_language("en")

    # discovery.xhtml has substring 'cover', recovery.xhtml has 'cover', stock.xhtml has 'toc'
    ch1 = epub.EpubHtml(title="Discovery", file_name="discovery.xhtml", lang="en")
    ch1.set_content("<h1>Chapter 1: Discovery</h1><p>We embarked upon the vast uncharted seas.</p>")
    ch2 = epub.EpubHtml(title="Stock Analysis", file_name="stock.xhtml", lang="en")
    ch2.set_content("<h2>Chapter 2: Stock</h2><p>Capital asset allocation strategies.</p>")

    book.add_item(ch1)
    book.add_item(ch2)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", ch1, ch2]

    epub_path = tmp_path / "test_discovery.epub"
    epub.write_epub(str(epub_path), book)

    parsed = parse_epub(epub_path)
    assert len(parsed.chapters) == 2
    assert "Discovery" in parsed.chapters[0].title
    assert "Stock" in parsed.chapters[1].title
