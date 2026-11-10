from pathlib import Path

import pytest

from cantoleaf.export.lyrics import export_lrc_manifest, export_srt_manifest
from cantoleaf.export.m4b import master_m4b_audiobook
from cantoleaf.export.vault import export_anki_deck, export_obsidian_marginalia
from cantoleaf.models import BlockKind, DepthGear, LangMode, SynthesizedSpan, Utterance, WordTiming
from cantoleaf.providers.adapt.extractive import ExtractiveAdaptProvider
from cantoleaf.workflows.retention import generate_recall_lock_utterances


@pytest.mark.asyncio
async def test_socratic_recall_locks() -> None:
    adapt = ExtractiveAdaptProvider()
    utterances = await generate_recall_lock_utterances(
        "book1", 0, "Chapter 1", "The linear constraint of books.", adapt
    )
    assert len(utterances) >= 3
    assert utterances[0].spoken_text.startswith("Active Recall")
    # Thinking pause is 4000ms
    assert utterances[1].pause_after_ms == 4000


def test_obsidian_and_anki_export(tmp_path: Path) -> None:
    u = Utterance(
        utterance_id="b:c0:b1:verbatim:src:u0",
        chapter_index=0,
        block_index=1,
        gear=DepthGear.VERBATIM,
        lang_mode=LangMode.SOURCE,
        block_kind=BlockKind.PROSE,
        source_text="Attention is the bottleneck of human learning.",
        spoken_text="Attention is the bottleneck of human learning.",
    )
    md_file = export_obsidian_marginalia("Cognitive Habits", "Author X", "Chapter 1", [u], tmp_path)
    assert md_file.exists()
    content = md_file.read_text(encoding="utf-8")
    assert "Attention is the bottleneck" in content
    assert "Author X" in content

    anki_file = export_anki_deck(
        "Cognitive Habits", [("What is the bottleneck?", "Attention.")], tmp_path
    )
    assert anki_file.exists()
    csv_content = anki_file.read_text(encoding="utf-8")
    assert "What is the bottleneck?,Attention." in csv_content


def test_lyrics_and_m4b_mastering(tmp_path: Path) -> None:
    # Create two tiny dummy wav files
    import numpy as np
    import soundfile as sf

    f1 = tmp_path / "clip1.wav"
    f2 = tmp_path / "clip2.wav"
    audio = np.zeros(24000, dtype=np.float32)
    sf.write(str(f1), audio, 24000)
    sf.write(str(f2), audio, 24000)

    spans = [
        SynthesizedSpan(
            utterance_id="u1",
            audio_path=f1,
            duration_sec=1.0,
            pause_after_sec=0.2,
            word_timings=(
                WordTiming(word="Hello", char_start=0, char_end=5, start_sec=0.0, end_sec=0.8),
            ),
            provider="fake",
            voice="v1",
        ),
        SynthesizedSpan(
            utterance_id="u2",
            audio_path=f2,
            duration_sec=1.0,
            pause_after_sec=0.2,
            word_timings=(
                WordTiming(word="World", char_start=0, char_end=5, start_sec=0.0, end_sec=0.8),
            ),
            provider="fake",
            voice="v1",
        ),
    ]

    lrc_path = export_lrc_manifest(spans, tmp_path / "book.lrc")
    assert lrc_path.exists()
    assert "[00:00.00]Hello" in lrc_path.read_text(encoding="utf-8")

    srt_path = export_srt_manifest(spans, ["Hello", "World"], tmp_path / "book.srt")
    assert srt_path.exists()
    assert "00:00:00,000 --> 00:00:01,000" in srt_path.read_text(encoding="utf-8")

    m4b_path = master_m4b_audiobook(
        spans,
        [("Chapter 1", 0.0, 1.0), ("Chapter 2", 1.0, 2.0)],
        tmp_path / "book.m4b",
        "Test Book",
        "Test Author",
    )
    assert m4b_path.exists()
    assert m4b_path.stat().st_size > 0
