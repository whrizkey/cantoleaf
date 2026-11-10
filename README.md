# CantoLeaf

[![CI](https://github.com/whrizkey/cantoleaf/actions/workflows/ci.yml/badge.svg)](https://github.com/whrizkey/cantoleaf/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy-lang.org/)

> **Status: v0.1.0 — Cognitive Audio Reader & Audiobook Studio**

**CantoLeaf** is an open-source, BYOK (Bring Your Own Key) & local-first **cognitive audio reader and audiobook studio** designed around how humans actually acquire knowledge from books.

Instead of treating books as flat, linear text dumps, CantoLeaf introduces **5 novel audio-knowledge workflows**:

1. **Elastic Depth Gearshifting (`Pulse ↔ Crux ↔ Verbatim + Unpack`)**: Listen at 3 density levels (3-min thesis skim, high-signal crux with filler anecdotes bridged, or 100% unabridged) and shift gears mid-chapter without losing your place.
2. **Bilingual Bridge (`Echo` & `Code-Switch` Modes)**: Sentence-by-sentence dual-language shadowing (Voice A speaks source, Voice B speaks target) or native prose with preserved technical terminology.
3. **Sonic Typography & Procedural Earcons**: Pure mathematical micro-chimes, quote resonance shifts, stereo "margin whispers" for footnotes, and spoken figure cards for tables and equations.
4. **Active Recall "Memory Locks" & 1-Tap Crystallize**: End-of-chapter Socratic retrieval checkpoints (`Question → 4s thinking pulse → Answer`) and 1-tap capture to **Obsidian Markdown** notes and **Anki flashcards**.
5. **Speculative TOC Pre-Warming & Hybrid M4B Mastering**: Sub-50ms instant jumping across any chapter in the book + chaptered `.m4b` export with embedded cover art and synchronized `.lrc`/`.srt` lyrics.

---

## Quickstart

```bash
# 1. Clone the repository
git clone https://github.com/whrizkey/cantoleaf.git
cd cantoleaf

# 2. Install dependencies with uv
uv sync --all-extras --dev

# 3. Check system environment & diagnostics
uv run cantoleaf doctor

# 4. Inspect document chapters & depth gear estimates
uv run cantoleaf estimate my_book.epub

# 5. Convert an eBook to a chaptered .m4b cognitive audiobook
uv run cantoleaf convert my_book.epub --gear crux -o audiobook.m4b

# 6. Or launch the interactive Web Studio
uv run cantoleaf studio
```

## Running Diagnostics & Tests

```bash
# Lint with ruff
uv run ruff check .

# Type-check with strict mypy
uv run mypy src tests

# Run offline test suite (38 unit and review regression tests)
uv run pytest
```

## License

[Apache 2.0](LICENSE) © 2026 whrizkey
