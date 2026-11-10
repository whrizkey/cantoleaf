import csv
from datetime import UTC, datetime
from pathlib import Path

from cantoleaf.models import Utterance


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
    """
    vault_dir.mkdir(parents=True, exist_ok=True)
    slug = book_title.lower().replace(" ", "_").replace(":", "")
    out_file = vault_dir / f"{slug}_notes.md"

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        f"# Marginalia: {book_title}",
        f"- **Author**: {author}",
        f"- **Captured**: {now}",
        f"- **Chapter**: {chapter_title}",
        "",
        "## Key Insights & Crystallized Passages",
        "",
    ]

    for u in utterances:
        lines.append(f'> "{u.source_text}"')
        lines.append(f"— *{chapter_title} (Block #{u.block_index})*")
        lines.append("")

    out_file.write_text("\n".join(lines), encoding="utf-8")
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
    slug = book_title.lower().replace(" ", "_").replace(":", "")
    out_file = deck_dir / f"{slug}_anki.csv"

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["#separator:Comma"])
        writer.writerow(["#html:false"])
        writer.writerow(["#tags column:3"])
        for q, a in qa_pairs:
            writer.writerow([q, a, f"cantoleaf::{slug}"])

    return out_file
