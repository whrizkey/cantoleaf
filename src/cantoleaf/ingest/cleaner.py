import re

# Regex for line-broken words: e.g. "com-\nputer" -> "computer"
HYPHEN_BREAK_RE = re.compile(r"(\b[a-zA-Z]{2,})-\s*\n\s*([a-zA-Z]{2,}\b)")

# Bracketed numeric and list citations: [1], [1, 2], [1-3], [12, 14, 18]
CITATION_RE = re.compile(r"\[\s*\d+(?:\s*[,–-]\s*\d+)*\s*\]")

# Author-year citations: (Vaswani et al., 2017) or (Smith, 2020; Jones, 2021)
AUTHOR_YEAR_RE = re.compile(
    r"\([A-Z][a-zA-Z\s.,]+(?:et al\.?)?,\s*\d{4}(?:;\s*[A-Z][a-zA-Z\s.,]+,\s*\d{4})*\)"
)

# URLs
URL_RE = re.compile(r"https?://[^\s)\]>]+")

# Multiple consecutive blank lines
CONSECUTIVE_BLANKS_RE = re.compile(r"\n{3,}")


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
    - Strips citation brackets like [1] or [12-14] that interrupt listening
    - Replaces raw web URLs with 'web link'
    - Normalizes irregular whitespace and quotes
    """
    res = text

    if dehyphenate:
        res = HYPHEN_BREAK_RE.sub(r"\1\2", res)

    if skip_citations:
        res = CITATION_RE.sub("", res)
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
