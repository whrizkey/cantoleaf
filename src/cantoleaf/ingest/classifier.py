from cantoleaf.models import BlockKind


def classify_block(text: str, is_heading: bool = False, is_quote: bool = False) -> BlockKind:
    """
    Classifies a text block into a semantic BlockKind to drive CantoLeaf's
    Depth Gearshifting and Sonic Typography workflows.
    """
    clean = text.strip()
    if is_heading or (clean.startswith("#") and len(clean.splitlines()) == 1):
        return BlockKind.HEADING

    if is_quote or clean.startswith(">"):
        return BlockKind.QUOTE

    if clean.startswith("```") or clean.startswith("    "):
        return BlockKind.CODE

    if clean.startswith("|") and clean.endswith("|") and "\n|" in clean:
        return BlockKind.TABLE

    if clean.startswith("$$") or clean.startswith("\\["):
        return BlockKind.EQUATION

    # Heuristic for narrative anecdotes vs core arguments
    lower = clean.lower()
    anecdote_markers = (
        "for example,",
        "for instance,",
        "one morning,",
        "years ago,",
        "i remember when",
        "in 199",
        "in 198",
        "in 200",
        "once upon a time",
        "consider the case of",
        "a friend of mine",
    )
    if any(lower.startswith(m) or f" {m}" in lower for m in anecdote_markers) and len(clean) > 50:
        return BlockKind.ANECDOTE

    return BlockKind.PROSE
