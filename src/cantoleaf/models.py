from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class DepthGear(StrEnum):
    PULSE = "pulse"  # Gear 1: ~10% length (Thesis & key takeaways rail)
    CRUX = "crux"  # Gear 2: ~55% length (Core arguments verbatim, anecdotes bridged)
    VERBATIM = "verbatim"  # Gear 3: 100% length (Unabridged cleaned text)
    UNPACK = "unpack"  # Gear 4: On-demand plain-language analogy/explanation branch


class BlockKind(StrEnum):
    HEADING = "heading"
    PROSE = "prose"
    ANECDOTE = "anecdote"
    QUOTE = "quote"
    FOOTNOTE = "footnote"
    TABLE = "table"
    EQUATION = "equation"
    CODE = "code"
    RECALL_LOCK = "recall_lock"


class LangMode(StrEnum):
    SOURCE = "source"  # Original language
    TARGET = "target"  # Full target language translation
    ECHO = "echo"  # Interleaved: Source sentence (Voice A) -> Target sentence (Voice B)
    CODE_SWITCH = "code_switch"  # Target prose with original domain terminology preserved


@dataclass(frozen=True)
class WordTiming:
    word: str
    char_start: int
    char_end: int
    start_sec: float
    end_sec: float


@dataclass(frozen=True)
class Utterance:
    utterance_id: str  # f"{book_id}:ch{ch}:b{blk}:{gear}:{lang_mode}:u{idx}"
    chapter_index: int
    block_index: int  # Shared anchor across all DepthGears
    gear: DepthGear
    lang_mode: LangMode
    block_kind: BlockKind
    source_text: str
    spoken_text: str
    voice_role: str = "primary"  # "primary" | "secondary_echo" | "margin_whisper" | "socratic_host"
    earcon_before: str | None = None
    earcon_after: str | None = None
    pause_after_ms: int = 350


@dataclass(frozen=True)
class SynthesizedSpan:
    utterance_id: str
    audio_path: Path
    duration_sec: float
    pause_after_sec: float
    word_timings: tuple[WordTiming, ...]
    provider: str
    voice: str


@dataclass(frozen=True)
class SemanticBlock:
    block_index: int
    kind: BlockKind
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Chapter:
    index: int
    title: str
    blocks: tuple[SemanticBlock, ...]
    estimated_chars: int


@dataclass(frozen=True)
class BookMetadata:
    book_id: str
    title: str
    author: str
    language: str
    chapters: tuple[Chapter, ...]
    cover_image: Path | None = None
