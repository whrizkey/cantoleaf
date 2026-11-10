import subprocess
from pathlib import Path

from cantoleaf.errors import SynthesisError
from cantoleaf.models import SynthesizedSpan


def master_m4b_audiobook(
    spans: list[SynthesizedSpan],
    chapter_markers: list[tuple[str, float, float]],  # (title, start_sec, end_sec)
    out_file: Path,
    book_title: str,
    author: str,
    cover_image: Path | None = None,
) -> Path:
    """
    Masters a chaptered .m4b AAC audiobook with metadata and embedded chapters
    using ffmpeg concat demuxer to avoid loading massive PCM buffers into memory.
    """
    out_file.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = out_file.parent / ".tmp_master"
    temp_dir.mkdir(parents=True, exist_ok=True)

    concat_list = temp_dir / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for span in spans:
            f.write(f"file '{span.audio_path.resolve()}'\n")

    # Generate FFMETADATA1 file
    meta_file = temp_dir / "ffmetadata.txt"
    meta_lines = [
        ";FFMETADATA1",
        f"title={book_title}",
        f"artist={author}",
        f"album={book_title}",
        "comment=Mastered with CantoLeaf Cognitive Audio Studio",
    ]

    for title, start_s, end_s in chapter_markers:
        meta_lines.extend([
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={int(start_s * 1000)}",
            f"END={int(end_s * 1000)}",
            f"title={title}",
        ])

    meta_file.write_text("\n".join(meta_lines), encoding="utf-8")

    # Run ffmpeg to encode to AAC / .m4b
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-i", str(meta_file),
        "-map_metadata", "1",
        "-c:a", "aac", "-b:a", "64k",
        "-vn",
        str(out_file),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise SynthesisError(f"ffmpeg m4b mastering failed: {e.stderr.decode()}") from e
    finally:
        # Cleanup temporary concat files
        if concat_list.exists():
            concat_list.unlink()
        if meta_file.exists():
            meta_file.unlink()

    return out_file
