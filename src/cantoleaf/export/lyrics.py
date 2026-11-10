from pathlib import Path

from cantoleaf.models import SynthesizedSpan


def export_lrc_manifest(
    spans: list[SynthesizedSpan],
    out_path: Path,
    title: str = "Audiobook",
    artist: str = "CantoLeaf",
) -> Path:
    """
    Exports exact synchronized .lrc lyrics file matching external players (VLC, mpv, Audiobookshelf).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"[ti:{title}]",
        f"[ar:{artist}]",
        "[al:CantoLeaf Audio Edition]",
        "[by:CantoLeaf Cognitive Reader]",
    ]

    timeline_s = 0.0
    for span in spans:
        for wt in span.word_timings:
            w_time = timeline_s + wt.start_sec
            minutes = int(w_time // 60)
            seconds = int(w_time % 60)
            hundredths = int((w_time - int(w_time)) * 100)
            lines.append(f"[{minutes:02d}:{seconds:02d}.{hundredths:02d}]{wt.word}")

        timeline_s += span.duration_sec + span.pause_after_sec

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def export_srt_manifest(
    spans: list[SynthesizedSpan],
    utterance_texts: list[str] | None = None,
    out_path: Path | None = None,
) -> Path:
    """Exports sentence-level .srt subtitle file."""
    if out_path is None:
        raise ValueError("out_path is required")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    entries: list[str] = []
    timeline_s = 0.0

    texts: list[str] = []
    if utterance_texts is not None:
        texts = utterance_texts
    else:
        for s in spans:
            if s.word_timings:
                texts.append(" ".join(wt.word for wt in s.word_timings))
            else:
                texts.append(s.utterance_id)

    for i, (span, text) in enumerate(zip(spans, texts, strict=False)):
        start_t = timeline_s
        end_t = timeline_s + span.duration_sec

        def fmt_time(t: float) -> str:
            hrs = int(t // 3600)
            mins = int((t % 3600) // 60)
            secs = int(t % 60)
            millis = int((t - int(t)) * 1000)
            return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

        entries.append(f"{i + 1}\n{fmt_time(start_t)} --> {fmt_time(end_t)}\n{text}\n")
        timeline_s += span.duration_sec + span.pause_after_sec

    out_path.write_text("\n".join(entries), encoding="utf-8")
    return out_path


export_lrc = export_lrc_manifest


def export_srt(
    spans: list[SynthesizedSpan],
    out_path: Path,
    utterance_texts: list[str] | None = None,
) -> Path:
    return export_srt_manifest(spans, utterance_texts, out_path)
