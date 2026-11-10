from cantoleaf.ingest.cleaner import clean_text
from cantoleaf.ingest.segmenter import split_into_sentences


def test_cleaner_dehyphenation() -> None:
    text = "This is a demon-\nstration of de-hyphenation."
    cleaned = clean_text(text)
    assert "demonstration" in cleaned


def test_cleaner_citation_removal() -> None:
    text = "The transformer model [1] revolutionized AI [2, 4–6]. Later work (Vaswani et al., 2017) confirmed this."
    cleaned = clean_text(text)
    assert "[1]" not in cleaned
    assert "[2, 4–6]" not in cleaned
    assert "Vaswani" not in cleaned
    assert "transformer model revolutionized AI." in cleaned


def test_cleaner_url_simplification() -> None:
    text = "Read more at https://example.com/research/paper for details."
    cleaned = clean_text(text)
    assert "https://" not in cleaned
    assert "web link" in cleaned


def test_segmenter_abbreviations() -> None:
    text = "Dr. Smith went to Washington D.C. to meet Mr. Brown. It was 9:00 a.m. He was happy."
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "Dr. Smith went to Washington D.C. to meet Mr. Brown."
    assert sentences[1] == "It was 9:00 a.m."
    assert sentences[2] == "He was happy."


def test_segmenter_cjk() -> None:
    text = "这是第一句话。这是第二句话！还有第三句吗？"
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "这是第一句话。"
    assert sentences[1] == "这是第二句话！"
    assert sentences[2] == "还有第三句吗？"
