import hashlib
import json
import sqlite3
from pathlib import Path

from cantoleaf.models import SynthesizedSpan, WordTiming


class AudioCache:
    """
    SQLite WAL + Content-Addressed File Cache:
    Stores synthesized audio and exact word alignment timings keyed by content hash.
    Ensures that re-reading or switching between Crux and Verbatim never synthesizes the same block twice!
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or Path("~/.cantoleaf/cache/cantoleaf.db").expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS synthesis_cache (
                    cache_key TEXT PRIMARY KEY,
                    utterance_id TEXT,
                    audio_path TEXT,
                    duration_sec REAL,
                    pause_after_sec REAL,
                    word_timings_json TEXT,
                    provider TEXT,
                    voice TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    @staticmethod
    def compute_key(text: str, provider: str, voice: str, rate: float) -> str:
        raw = f"{text.strip()}::{provider}::{voice}::{rate:.2f}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, text: str, provider: str, voice: str, rate: float) -> SynthesizedSpan | None:
        key = self.compute_key(text, provider, voice, rate)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT utterance_id, audio_path, duration_sec, pause_after_sec, word_timings_json, provider, voice FROM synthesis_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()

        if not row:
            return None

        audio_file = Path(row[1])
        if not audio_file.exists():
            return None

        timings_raw = json.loads(row[4])
        word_timings = tuple(
            WordTiming(
                word=item["word"],
                char_start=item["char_start"],
                char_end=item["char_end"],
                start_sec=item["start_sec"],
                end_sec=item["end_sec"],
            )
            for item in timings_raw
        )

        return SynthesizedSpan(
            utterance_id=row[0],
            audio_path=audio_file,
            duration_sec=row[2],
            pause_after_sec=row[3],
            word_timings=word_timings,
            provider=row[5],
            voice=row[6],
        )

    def put(self, text: str, rate: float, span: SynthesizedSpan) -> None:
        key = self.compute_key(text, span.provider, span.voice, rate)
        timings_data = [
            {
                "word": wt.word,
                "char_start": wt.char_start,
                "char_end": wt.char_end,
                "start_sec": wt.start_sec,
                "end_sec": wt.end_sec,
            }
            for wt in span.word_timings
        ]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO synthesis_cache
                (cache_key, utterance_id, audio_path, duration_sec, pause_after_sec, word_timings_json, provider, voice)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key,
                    span.utterance_id,
                    str(span.audio_path),
                    span.duration_sec,
                    span.pause_after_sec,
                    json.dumps(timings_data),
                    span.provider,
                    span.voice,
                ),
            )
