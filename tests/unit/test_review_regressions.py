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


@pytest.mark.asyncio
async def test_regression_pipeline_cache_hit_on_default_voice(tmp_path: Path) -> None:
    """Bug 1: SynthesisPipeline resolves default voice upfront so cache hits with voice=None."""
    from cantoleaf.pipeline.synthesizer import SynthesisPipeline
    from cantoleaf.providers.tts.fake import FakeTtsProvider

    cache = AudioCache(db_path=tmp_path / "cache.db")
    provider = FakeTtsProvider(cache_dir=tmp_path / "audio")
    pipeline = SynthesisPipeline(provider, cache)

    u = Utterance(
        utterance_id="test:ch0:b0:verbatim:source:u0",
        chapter_index=0,
        block_index=0,
        gear=DepthGear.VERBATIM,
        lang_mode=LangMode.SOURCE,
        block_kind=BlockKind.PROSE,
        source_text="Consistent voice caching check.",
        spoken_text="Consistent voice caching check.",
    )

    # First synthesis: writes to cache under provider.default_voice
    span1 = await pipeline.synthesize_utterance(u, voice=None)
    assert span1.voice == provider.default_voice

    # Second synthesis: queries with voice=None -> must HIT cache without re-synthesizing
    span2 = await pipeline.synthesize_utterance(u, voice=None)
    assert span2.audio_path == span1.audio_path


def test_regression_cleaner_attached_citations_and_dates() -> None:
    """Attached citations like claim[3] stripped; entity dates (Berlin, 1989) and (Apple, 1976) preserved."""
    # Attached citation without preceding space
    text1 = "This verified claim[3] holds true."
    cleaned1 = clean_text(text1)
    assert "[3]" not in cleaned1
    assert "claim" in cleaned1

    # Historical and corporate dates in parentheses
    text2 = "The wall fell (Berlin, 1989) and a company was founded (Apple, 1976)."
    cleaned2 = clean_text(text2)
    assert "(Berlin, 1989)" in cleaned2
    assert "(Apple, 1976)" in cleaned2

    # Academic author citations must be stripped
    text3 = "Earlier works (Smith & Jones, 1999) and (Taylor et al., 2021) showed this."
    cleaned3 = clean_text(text3)
    assert "(Smith & Jones, 1999)" not in cleaned3
    assert "(Taylor et al., 2021)" not in cleaned3


def test_regression_classifier_markdown_list_not_footnote() -> None:
    """Markdown list items starting with '* Item' are classified as PROSE, not FOOTNOTE."""
    bullet = "* First key architectural principle"
    assert classify_block(bullet) == BlockKind.PROSE

    footnote = "[^1]: Detailed explanation of the parameter"
    assert classify_block(footnote) == BlockKind.FOOTNOTE


def test_regression_srt_subtitle_contains_spoken_text(tmp_path: Path) -> None:
    """SRT subtitles must contain the spoken sentence text, not utterance IDs."""
    from cantoleaf.export.lyrics import export_srt
    from cantoleaf.models import WordTiming

    span = SynthesizedSpan(
        utterance_id="audiobook:ch0:b0:verbatim:source:u0",
        audio_path=tmp_path / "dummy.mp3",
        duration_sec=2.5,
        pause_after_sec=0.35,
        word_timings=(
            WordTiming(word="The", char_start=0, char_end=3, start_sec=0.0, end_sec=0.5),
            WordTiming(word="mind", char_start=4, char_end=8, start_sec=0.5, end_sec=1.2),
            WordTiming(word="wanders.", char_start=9, char_end=17, start_sec=1.2, end_sec=2.5),
        ),
        provider="fake",
        voice="default",
    )

    srt_file = tmp_path / "output.srt"

    # Test 1: explicit spoken text list passed
    export_srt([span], srt_file, ["The mind wanders."])
    content1 = srt_file.read_text(encoding="utf-8")
    assert "The mind wanders." in content1
    assert "audiobook:ch0:b0" not in content1

    # Test 2: fallback extracts words from word_timings
    export_srt([span], srt_file)
    content2 = srt_file.read_text(encoding="utf-8")
    assert "The mind wanders." in content2
    assert "audiobook:ch0:b0" not in content2


def test_regression_non_latin_slug_sanitization(tmp_path: Path) -> None:
    """Non-Latin book titles (e.g. Japanese, Cyrillic) preserve Unicode characters instead of collapsing to 'untitled'."""
    from cantoleaf.export.vault import _sanitize_slug, export_obsidian_marginalia

    slug_jp = _sanitize_slug("吾輩は猫である")
    assert slug_jp == "吾輩は猫である"

    slug_cyrillic = _sanitize_slug("Война и мир")
    assert slug_cyrillic == "Война_и_мир"

    u = Utterance(
        utterance_id="u1",
        chapter_index=0,
        block_index=0,
        gear=DepthGear.VERBATIM,
        lang_mode=LangMode.SOURCE,
        block_kind=BlockKind.PROSE,
        source_text="吾輩は猫である。名前はまだ無い。",
        spoken_text="吾輩は猫である。名前はまだ無い。",
    )
    saved = export_obsidian_marginalia("吾輩は猫である", "夏目漱石", "第1章", [u], tmp_path)
    assert "吾輩は猫である" in saved.name
    assert saved.exists()


@pytest.mark.asyncio
async def test_regression_web_studio_security_and_crystallize(tmp_path: Path) -> None:
    """Web Studio rejects path traversal and glob injection, and supports note crystallization."""
    from fastapi.testclient import TestClient

    from cantoleaf.web.app import app

    client = TestClient(app)

    # 1. Path traversal / absolute system file access rejected (403)
    resp_traversal = client.get("/api/book/inspect?path=/etc/passwd")
    assert resp_traversal.status_code == 403

    # 2. Glob pattern in audio filename rejected (400)
    resp_audio_glob = client.get("/api/audio/*.mp3")
    assert resp_audio_glob.status_code == 400

    # 3. Crystallize endpoint saves note
    resp_cryst = client.post(
        "/api/chapter/crystallize",
        json={
            "book_title": "Mind in Motion",
            "author": "Cognitive Author",
            "chapter_title": "Chapter 1",
            "source_text": "Crystallized core insight.",
            "block_index": 3,
            "vault_dir": str(tmp_path / "notes"),
        },
    )
    assert resp_cryst.status_code == 200
    assert resp_cryst.json()["status"] == "saved"
    saved_note = Path(resp_cryst.json()["path"])
    assert saved_note.exists()
    assert "Crystallized core insight." in saved_note.read_text(encoding="utf-8")
