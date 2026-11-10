import re

from cantoleaf.models import BlockKind

FOOTNOTE_PATTERN = re.compile(r"^(?:\[\^[\w\-]+\]:|\[\d+\]\s+[A-Z]|(?:\*|\u2020|\u2021)\s+[A-Z])")


def classify_block(
    text: str,
    is_heading: bool = False,
    is_quote: bool = False,
    is_footnote: bool = False,
) -> BlockKind:
    """
    Classifies a text block into a semantic BlockKind to drive CantoLeaf's
    Depth Gearshifting, Sonic Typography, and Margin Whisper workflows.
    """
    # Check for indented code before stripping whitespace
    if text.startswith("    ") or text.startswith("\t"):
        return BlockKind.CODE

    clean = text.strip()
    if is_footnote or bool(FOOTNOTE_PATTERN.match(clean)):
        return BlockKind.FOOTNOTE

    if is_heading or (clean.startswith("#") and len(clean.splitlines()) == 1):
        return BlockKind.HEADING

    if is_quote or clean.startswith(">"):
        return BlockKind.QUOTE

    if clean.startswith("```"):
        return BlockKind.CODE

    if clean.startswith("|") and clean.endswith("|") and "\n|" in clean:
        return BlockKind.TABLE

    if clean.startswith("$$") or clean.startswith("\\["):
        return BlockKind.EQUATION

    # Anecdote detection: Must start with narrative framing or date opening
    lower = clean.lower()
    opening_anecdotes = (
        "for example,",
        "for instance,",
        "one morning,",
        "years ago,",
        "i remember when",
        "once upon a time",
        "consider the case of",
        "a friend of mine",
    )
    is_anecdote = any(lower.startswith(p) for p in opening_anecdotes)
    if is_anecdote and len(clean) > 100:
        return BlockKind.ANECDOTE

    return BlockKind.PROSE
