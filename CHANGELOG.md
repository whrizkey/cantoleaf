# Changelog

All notable changes to **CantoLeaf** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-09

### Added
- **Core Architecture & AST Ingestion**:
  - Parsers for `.epub` (EPUB 2/3), `.pdf` (with geometric running header/footer rejection), `.docx`, `.md`, and `.txt`.
  - Smart text cleaner with de-hyphenation, citation/URL stripping, and typographic normalization.
  - Abbreviation- and CJK-aware sentence segmenter.
- **Workflow 1: Elastic Depth Gears**:
  - `Pulse` (3-minute thesis & takeaway rail).
  - `Crux` (high-signal core arguments verbatim with anecdote case summaries bridged).
  - `Verbatim` (100% unabridged).
  - Shared `block_index` anchors enabling instant mid-chapter gearshifts without position loss.
- **Workflow 2: The Bilingual Bridge**:
  - `source`, `target`, `echo` (dual-voice sentence shadowing), and `code_switch` (native prose with original domain terms).
- **Workflow 3: Sonic Typography & Procedural Earcons**:
  - Pure `numpy` harmonic chimes for headings, quotes, and narrated table figure cards.
- **Workflow 4: Active Recall Checkpoints & Crystallize**:
  - Socratic Memory Locks (`Question → 4s thinking pulse → Answer`).
  - 1-tap crystallization to Obsidian Markdown notes and Anki flashcards.
- **Workflow 5: Speculative TOC & Audiobook Mastering**:
  - LookaheadScheduler with speculative pre-warming of opening sentences for sub-50ms chapter jumping.
  - Chaptered `.m4b` AAC mastering using ffmpeg concat demuxer with embedded TOC and cover art.
  - Exact `.lrc` and `.srt` subtitle/lyrics synchronization.
- **BYOK & Local Provider Stack**:
  - Microsoft Edge TTS (free, zero-key, native WordBoundary alignment).
  - ElevenLabs BYOK with character/word timestamp parsing.
  - OpenAI-compatible TTS (OpenAI, Groq, Kokoro-FastAPI, LocalAI).
  - 100% offline Extractive adapter (zero LLM keys needed).
- **User Interfaces**:
  - CLI: `cantoleaf doctor`, `cantoleaf estimate`, `cantoleaf version`.
  - Responsive Web Studio SPA with live Depth Gearshift slider, word-by-word active highlighting, and export drawer.
