import re

# Regex for line-broken words: e.g. "com-\nputer" -> "computer"
HYPHEN_BREAK_RE = re.compile(r"(\b[a-zA-Z]{2,})-\s*\n\s*([a-zA-Z]{2,}\b)")

# Bracketed numeric citations regex pattern
CITE_PATTERN = re.compile(r"(\b[a-zA-Z0-9_]+\b|[^\w\s]|\s|^)(\[\s*\d+(?:\s*[,–-]\s*\d+)*\s*\])")

# Author-year citations: require multiple authors, "et al.", semicolons, or page numbers
# Preserves location/company parentheticals like (Berlin, 1989), (Apple, 1976), (New York, 1999)
AUTHOR_YEAR_RE = re.compile(
    r"\([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+|\s+et\s+al\.?),\s*\d{4}[a-z]?(?:;\s*[A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+|\s+et\s+al\.?)?,\s*\d{4}[a-z]?)*(?:,\s*p{1,2}\.?\s*\d+)?\)"
    r"|\([A-Z][a-z]+,\s*\d{4}[a-z]?(?:;\s*[A-Z][a-z]+,\s*\d{4}[a-z]?)+(?:,\s*p{1,2}\.?\s*\d+)?\)"
    r"|\([A-Z][a-z]+,\s*\d{4}[a-z]?,\s*p{1,2}\.?\s*\d+\)"
)

# URLs
URL_RE = re.compile(r"https?://[^\s)\]>]+")

# Multiple consecutive blank lines
CONSECUTIVE_BLANKS_RE = re.compile(r"\n{3,}")


def _strip_bracket_citations(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        pre = m.group(1) or ""
        # Preserve single-letter variable indexing like x[1]
        if len(pre) == 1 and pre.isalpha():
            return m.group(0)
        return pre

    return CITE_PATTERN.sub(repl, text)


def clean_text(
    text: str,
    *,
    skip_citations: bool = True,
    simplify_urls: bool = True,
    dehyphenate: bool = True,
) -> str:
    """
    Cleans raw document text for high-quality audio narration:
    - Repairs words broken across lines with hyphens
    - Strips citation brackets like [1] or claim[3] while preserving code like x[1]
    - Strips author-year citations while preserving historical parentheticals like (Berlin, 1989)
    - Replaces raw web URLs with 'web link'
    - Normalizes irregular whitespace and quotes
    """
    res = text

    if dehyphenate:
        res = HYPHEN_BREAK_RE.sub(r"\1\2", res)

    if skip_citations:
        res = _strip_bracket_citations(res)
        res = AUTHOR_YEAR_RE.sub("", res)

    if simplify_urls:
        res = URL_RE.sub("web link", res)

    # Clean up spaces before punctuation caused by citation stripping (e.g. "AI ." -> "AI.")
    res = re.sub(r"\s+([.,;:!?])", r"\1", res)

    # Normalize typographic quotes and dashes
    res = res.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    res = res.replace("—", " — ").replace("–", " – ")

    # Collapse multiple consecutive whitespaces/newlines
    res = re.sub(r"[ \t]+", " ", res)
    res = CONSECUTIVE_BLANKS_RE.sub("\n\n", res)

    return res.strip()
