import csv
import re
from datetime import UTC, datetime
from pathlib import Path

from cantoleaf.models import Utterance


def _sanitize_slug(text: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", text.strip(), flags=re.UNICODE).strip("_")
    return cleaned or "untitled"


def export_obsidian_marginalia(
    book_title: str,
    author: str,
    chapter_title: str,
    utterances: list[Utterance],
    vault_dir: Path,
) -> Path:
    """
    Exports crystallized spoken passages to an Obsidian-compatible Markdown note
    complete with book metadata, chapter citations, and pull-quotes.
    Appends subsequent chapters so earlier chapters are never overwritten.
    Prevents duplicate chapter appends on re-runs.
    """
    vault_dir.mkdir(parents=True, exist_ok=True)
    slug = _sanitize_slug(book_title)
    out_file = (vault_dir / f"{slug}_notes.md").resolve()

    # Prevent directory traversal
    if not out_file.is_relative_to(vault_dir.resolve()):
        out_file = vault_dir / "marginalia_notes.md"

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    if not out_file.exists():
        lines: list[str] = [
            f"# Marginalia: {book_title}",
            f"- **Author**: {author}",
            f"- **Captured**: {now}",
            "",
            "## Key Insights & Crystallized Passages",
            "",
            f"### {chapter_title}",
            "",
        ]
    else:
        existing_text = out_file.read_text(encoding="utf-8")
        if f"### {chapter_title}" in existing_text:
            # Already exported this chapter; do not duplicate
            return out_file

        lines = [
            "",
            f"### {chapter_title}",
            f"*Captured: {now}*",
            "",
        ]

    for u in utterances:
        lines.append(f'> "{u.source_text}"')
        lines.append(f"— *{chapter_title} (Block #{u.block_index})*")
        lines.append("")

    with open(out_file, "a" if out_file.exists() else "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return out_file


def export_anki_deck(
    book_title: str,
    qa_pairs: list[tuple[str, str]],
    deck_dir: Path,
) -> Path:
    """
    Exports Socratic Recall Locks into an Anki-compatible CSV deck (Front, Back, Tags).
    """
    deck_dir.mkdir(parents=True, exist_ok=True)
    slug = _sanitize_slug(book_title)
    out_file = (deck_dir / f"{slug}_anki.csv").resolve()

    if not out_file.is_relative_to(deck_dir.resolve()):
        out_file = deck_dir / "deck_anki.csv"

    file_exists = out_file.exists()
    with open(out_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["#separator:Comma"])
            writer.writerow(["#html:false"])
            writer.writerow(["#tags column:3"])
        for q, a in qa_pairs:
            writer.writerow([q, a, f"cantoleaf::{slug}"])

    return out_file
