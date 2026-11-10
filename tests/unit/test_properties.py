import pytest
from hypothesis import given, strategies as st
from cantoleaf.ingest.segmenter import split_into_sentences
from cantoleaf.ingest.cleaner import clean_text


@given(st.text(min_size=1, max_size=500))
def test_clean_text_never_crashes(text: str) -> None:
    cleaned = clean_text(text)
    assert isinstance(cleaned, str)


@given(st.text(min_size=1, max_size=500))
def test_segmenter_never_crashes(text: str) -> None:
    sentences = split_into_sentences(text)
    assert isinstance(sentences, list)
    for s in sentences:
        assert isinstance(s, str)
