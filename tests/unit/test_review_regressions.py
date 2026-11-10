from pathlib import Path

import pytest

from cantoleaf.errors import BudgetExceededError
from cantoleaf.export.m4b import _escape_ffmetadata
from cantoleaf.export.vault import export_obsidian_marginalia
from cantoleaf.ingest.classifier import classify_block
from cantoleaf.ingest.cleaner import clean_text
from cantoleaf.ingest.segmenter import split_into_sentences
from cantoleaf.models import BlockKind, DepthGear, LangMode, SynthesizedSpan, Utterance
from cantoleaf.pipeline.accounting import UsageTracker
from cantoleaf.pipeline.cache import AudioCache


def test_regression_bug_1_and_2_cache_keys(tmp_path: Path) -> None:
    """Bug 1 & 2: Cache keys differentiate voice, rate, block_kind, and earcons."""
    cache = AudioCache(db_path=tmp_path / "cache.db")
    dummy_wav = tmp_path / "dummy.wav"
    dummy_wav.write_bytes(b"dummy audio")

    span_v1 = SynthesizedSpan(
        utterance_id="u1",
        audio_path=dummy_wav,
        duration_sec=1.5,
        pause_after_sec=0.35,
        word_timings=(),
        provider="test",
        voice="voice_a",
    )
    cache.put("Hello world", 1.0, span_v1, block_kind=BlockKind.PROSE, enable_earcons=False)

    # Different voice -> should miss cache
    assert cache.get("Hello world", "test", "voice_b", 1.0, block_kind=BlockKind.PROSE) is None
    # Same voice, different rate -> should miss cache
    assert cache.get("Hello world", "test", "voice_a", 1.25, block_kind=BlockKind.PROSE) is None
    # Different block kind -> should miss cache
    assert cache.get("Hello world", "test", "voice_a", 1.0, block_kind=BlockKind.HEADING) is None
    # With earcons -> should miss cache
    assert (
        cache.get(
            "Hello world", "test", "voice_a", 1.0, block_kind=BlockKind.PROSE, enable_earcons=True
        )
        is None
    )
    # Exact match -> should hit
    hit = cache.get(
        "Hello world", "test", "voice_a", 1.0, block_kind=BlockKind.PROSE, enable_earcons=False
    )
    assert hit is not None
    assert hit.utterance_id == "u1"


def test_regression_bug_5_and_6_classifier() -> None:
    """Bug 5 & 6: Code indentation checked before strip; anecdote checked at start only."""
    # Indented code
    code_text = "    def foo():\n        return 42"
    assert classify_block(code_text) == BlockKind.CODE

    # Anecdote in middle of sentence should NOT be flagged as anecdote
    mid_sentence = (
        "The team evaluated the results, for example, during the quarterly review meeting."
    )
    assert classify_block(mid_sentence) == BlockKind.PROSE

    # Opening anecdote > 100 chars
    real_anecdote = "For example, consider the remarkable case where an entire electrical substation failed unexpectedly after a thunder storm struck."
    assert classify_block(real_anecdote) == BlockKind.ANECDOTE


def test_regression_bug_7_cleaner_citations() -> None:
    """Bug 7: (New York, 1999) preserved; x[1] preserved; [1] reference citation stripped."""
    # City + year parenthetical must NOT be stripped
    text_city = "He lived in (New York, 1999) before moving to Boston."
    cleaned_city = clean_text(text_city)
    assert "(New York, 1999)" in cleaned_city

    # Code array indexing x[1] must NOT be stripped
    text_code = "The variable x[1] holds the primary index."
    cleaned_code = clean_text(text_code)
    assert "x[1]" in cleaned_code

    # Real reference citation [1] must be stripped
    text_cite = "Deep learning revolutionized speech synthesis [1]."
    cleaned_cite = clean_text(text_cite)
    assert "[1]" not in cleaned_cite
    assert cleaned_cite == "Deep learning revolutionized speech synthesis."


def test_regression_bug_8_segmenter_abbreviations() -> None:
    """Bug 8: Regular words ending in periods (no., ed., app.) not over-merged; Ph.D. preserved."""
    text1 = "The answer was no. She left the room."
    sentences1 = split_into_sentences(text1)
    assert len(sentences1) == 2
    assert sentences1[0] == "The answer was no."
    assert sentences1[1] == "She left the room."

    text2 = "The Ph.D. student completed her research."
    sentences2 = split_into_sentences(text2)
    assert len(sentences2) == 1
    assert "Ph.D." in sentences2[0]


def test_regression_bug_10_vault_slug_and_append(tmp_path: Path) -> None:
    """Bug 10: Vault export sanitizes slug against path traversal and appends chapters."""
    vault = tmp_path / "vault"
    malicious_title = "../../etc/passwd"
    u1 = Utterance(
        utterance_id="u1",
        chapter_index=0,
        block_index=0,
        gear=DepthGear.VERBATIM,
        lang_mode=LangMode.SOURCE,
        block_kind=BlockKind.PROSE,
        source_text="First chapter quote.",
        spoken_text="First chapter quote.",
    )
    u2 = Utterance(
        utterance_id="u2",
        chapter_index=1,
        block_index=1,
        gear=DepthGear.VERBATIM,
        lang_mode=LangMode.SOURCE,
        block_kind=BlockKind.PROSE,
        source_text="Second chapter quote.",
        spoken_text="Second chapter quote.",
    )

    out1 = export_obsidian_marginalia(malicious_title, "Author", "Chapter 1", [u1], vault)
    assert out1.parent.resolve() == vault.resolve()
    assert ".." not in out1.name

    # Chapter 2 should append, NOT overwrite Chapter 1
    out2 = export_obsidian_marginalia(malicious_title, "Author", "Chapter 2", [u2], vault)
    assert out1 == out2
    content = out2.read_text(encoding="utf-8")
    assert "Chapter 1" in content
    assert "First chapter quote." in content
    assert "Chapter 2" in content
    assert "Second chapter quote." in content


def test_regression_bug_14_ffmetadata_escaping() -> None:
    """Bug 14: FFMETADATA special characters (=, ;, #, newline) escaped."""
    raw = "Title with = equal, ; semi, # hash\nand newline"
    escaped = _escape_ffmetadata(raw)
    assert "\\=" in escaped
    assert "\\;" in escaped
    assert "\\#" in escaped
    assert "\n" not in escaped


def test_regression_spend_cap_enforcement(tmp_path: Path) -> None:
    """Spend cap raises BudgetExceededError when character budget is crossed."""
    tracker = UsageTracker(max_budget_usd=0.01)
    # Elevenlabs rate in pricing.toml is $0.30 per 1k characters
    # 0.01 USD allows ~33 characters
    tracker.record_tts_usage("elevenlabs", 20)
    assert tracker.total_cost_usd > 0
    with pytest.raises(BudgetExceededError):
        tracker.record_tts_usage("elevenlabs", 1000)
