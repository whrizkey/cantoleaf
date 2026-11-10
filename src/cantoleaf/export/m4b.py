import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

from cantoleaf.errors import SynthesisError
from cantoleaf.models import SynthesizedSpan
from cantoleaf.workflows.earcons import generate_recall_tick


def _escape_ffmetadata(value: str) -> str:
    """Escapes special characters in FFMETADATA values: =, ;, #, \\, \n."""
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace("=", "\\=")
    escaped = escaped.replace(";", "\\;")
    escaped = escaped.replace("#", "\\#")
    return escaped.replace("\n", " ")


def master_m4b_audiobook(
    spans: list[SynthesizedSpan],
    chapter_markers: list[tuple[str, float, float]],  # (title, start_sec, end_sec)
    out_file: Path,
    book_title: str,
    author: str,
    cover_image: Path | None = None,
) -> Path:
    """
    Masters a chaptered .m4b AAC audiobook with metadata, cover art, and embedded chapters
    using ffmpeg concat demuxer. Renders exact pause_after_sec cushions (including
    Socratic recall ticks for 4s pauses) so subtitle timestamps and audio playback stay synchronized.
    """
    out_file.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = out_file.parent / ".tmp_master"
    temp_dir.mkdir(parents=True, exist_ok=True)

    concat_list = temp_dir / "concat_list.txt"
    silence_cache: dict[float, Path] = {}

    with open(concat_list, "w", encoding="utf-8") as f:
        for span in spans:
            # Escape single quotes in filenames for ffmpeg concat demuxer
            safe_path = str(span.audio_path.resolve()).replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

            # Render trailing pause silence cushion if pause_after_sec > 0
            if span.pause_after_sec > 0.01:
                pause_s = round(span.pause_after_sec, 3)
                if pause_s not in silence_cache:
                    silence_file = temp_dir / f"silence_{int(pause_s * 1000)}ms.wav"
                    sr = 24000
                    if abs(pause_s - 4.0) < 0.1:
                        # Render procedural Socratic recall tick pulses for the 4-second thinking interval
                        ticks = [generate_recall_tick(sr) for _ in range(4)]
                        silence_data = np.concatenate(ticks).astype(np.float32)
                    else:
                        silence_data = np.zeros(int(sr * pause_s), dtype=np.float32)
                    sf.write(str(silence_file), silence_data, sr)
                    silence_cache[pause_s] = silence_file

                safe_silence_path = str(silence_cache[pause_s].resolve()).replace("'", "'\\''")
                f.write(f"file '{safe_silence_path}'\n")

    # Generate FFMETADATA1 file with escaped title, artist, and chapter markers
    meta_file = temp_dir / "ffmetadata.txt"
    meta_lines = [
        ";FFMETADATA1",
        f"title={_escape_ffmetadata(book_title)}",
        f"artist={_escape_ffmetadata(author)}",
        f"album={_escape_ffmetadata(book_title)}",
        "comment=Mastered with CantoLeaf Cognitive Audio Studio",
    ]

    for title, start_s, end_s in chapter_markers:
        meta_lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={int(start_s * 1000)}",
                f"END={int(end_s * 1000)}",
                f"title={_escape_ffmetadata(title)}",
            ]
        )

    meta_file.write_text("\n".join(meta_lines), encoding="utf-8")

    # Build ffmpeg command with optional cover image
    has_cover = cover_image is not None and cover_image.exists()
    if has_cover and cover_image is not None:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-i",
            str(cover_image.resolve()),
            "-i",
            str(meta_file),
            "-map",
            "0:a",
            "-map",
            "1:v",
            "-map_metadata",
            "2",
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            "-c:v",
            "copy",
            "-disposition:v:0",
            "attached_pic",
            str(out_file),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-i",
            str(meta_file),
            "-map_metadata",
            "1",
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            "-vn",
            str(out_file),
        ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise SynthesisError(f"ffmpeg m4b mastering failed: {e.stderr.decode()}") from e
    finally:
        # Cleanup temporary concat and metadata files
        if concat_list.exists():
            concat_list.unlink()
        if meta_file.exists():
            meta_file.unlink()
        for sf_path in silence_cache.values():
            if sf_path.exists():
                sf_path.unlink()

    return out_file
