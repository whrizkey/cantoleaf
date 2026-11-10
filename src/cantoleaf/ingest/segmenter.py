import re

# Common abbreviations in English and other western languages to avoid false sentence splits
COMMON_ABBREVIATIONS = {
    "mr",
    "mrs",
    "ms",
    "dr",
    "prof",
    "sr",
    "jr",
    "vs",
    "etc",
    "fig",
    "al",
    "st",
    "ave",
    "blvd",
    "rd",
    "dept",
    "vol",
    "no",
    "rev",
    "hon",
    "gen",
    "col",
    "capt",
    "lt",
    "sgt",
    "gov",
    "sen",
    "rep",
    "jan",
    "feb",
    "mar",
    "apr",
    "aug",
    "sept",
    "oct",
    "nov",
    "dec",
    "approx",
    "app",
    "ed",
    "trans",
    "ca",
    "cf",
    "i.e",
    "e.g",
}

# Regex for sentence boundaries (Latin script: . ? ! followed by space/quote, or CJK fullwidth punctuation)
LATIN_SENTENCE_RE = re.compile(r'([.?!]+["\'\u201d\u2019)]*\s+)')
CJK_PUNCT_RE = re.compile(r"([。！？])")


def split_into_sentences(text: str) -> list[str]:
    """
    Splits paragraph text into sentences while respecting common abbreviations,
    numerical citations, decimal numbers, and CJK full-width punctuation.
    """
    clean_text = text.strip()
    if not clean_text:
        return []

    # First pass: Handle CJK punctuation if present
    if CJK_PUNCT_RE.search(clean_text):
        parts = CJK_PUNCT_RE.split(clean_text)
        sentences: list[str] = []
        for i in range(0, len(parts) - 1, 2):
            sent = (parts[i] + parts[i + 1]).strip()
            if sent:
                sentences.append(sent)
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())
        return sentences

    # Latin sentence splitting with lookaround and abbreviation protection
    tokens = LATIN_SENTENCE_RE.split(clean_text)
    candidates: list[str] = []
    i = 0
    while i < len(tokens):
        part = tokens[i]
        if i + 1 < len(tokens):
            punct = tokens[i + 1]
            candidate = part + punct
            i += 2
        else:
            candidate = part
            i += 1

        # While candidate ends with an abbreviation or acronym (e.g. "Dr. ", "D.C. "), merge next tokens
        while i < len(tokens):
            words = candidate.strip().split()
            if not (words and candidate.strip().endswith(".")):
                break
            last_word = words[-1].rstrip(".").lower()
            is_abbrev = (
                last_word in COMMON_ABBREVIATIONS
                or len(last_word) == 1
                or (len(last_word) == 3 and last_word[1] == ".")
            )
            # If next token begins with an uppercase letter, acronyms like a.m. or p.m. often end a sentence
            if is_abbrev and last_word in ("a.m", "p.m") and i < len(tokens):
                next_text = tokens[i].strip()
                if next_text and next_text[0].isupper():
                    break

            if not is_abbrev:
                break
            # Merge with next token
            next_part = tokens[i]
            i += 1
            if i < len(tokens):
                next_part += tokens[i]
                i += 1
            candidate += next_part

        if candidate.strip():
            candidates.append(candidate.strip())

    return candidates
