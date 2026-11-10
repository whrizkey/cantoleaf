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
  - Microsoft Edge TTS (free, zero-key, native WordBoundary alignment with cursor tracking).
  - ElevenLabs BYOK with character/word timestamp parsing and rate control.
  - OpenAI-compatible TTS (OpenAI, Groq, Kokoro-FastAPI, LocalAI).
  - 100% offline Extractive adapter (zero LLM keys needed).
  - OpenAI-compatible LLM adapter and DeepL API translation provider.
  - UsageTracker circuit breaker spend cap reading unit rates from `pricing.toml`.
- **User Interfaces**:
  - CLI: `cantoleaf convert` (batch .m4b synthesis), `cantoleaf listen`, `cantoleaf studio` (web reader launcher), `cantoleaf doctor`, `cantoleaf estimate`, `cantoleaf version`.
  - Responsive Web Studio SPA with live Depth Gearshift slider, real-time HTML5 audio playback with millisecond word highlighting, and .m4b export.
- **Review Bug Fixes (Rounds 1 & 2)**:
  - **Cache Key Symmetry & Default Voice**: Pre-resolved provider default voices upfront in `SynthesisPipeline` so cache checks and writes use identical concrete voice keys, eliminating cache misses on default voice.
  - **Output File Collision Prevention**: Hashed voice and speech rate into cached audio filenames across all providers (Edge, ElevenLabs, OpenAI, Fake), preventing cross-voice overwrites.
  - **Accurate Audio Durations**: Probed synthesized audio files with `soundfile.info()` to replace rough word-count approximations with actual audio durations.
  - **Spend Cap & Pricing Path Resolution**: Added multi-directory `find_pricing_path()` for `pricing.toml`, treated `<= 0` as unlimited spending without raising `BudgetExceededError`, added token-based `record_llm_usage()`, and exempted localhost/127.0.0.1 from usage costs.
  - **Web Studio Security**: Strictly validated document and export paths against allowed roots (`cwd`, `~/.cantoleaf`, `tempfile`), rejected path traversal and absolute system paths, enforced strict regex on audio filenames to eliminate glob wildcards, and used a global shared tracker to prevent budget resets across requests.
  - **Web Studio Place Retention**: Anchored playback across Depth Gears via `block_index` mapping so shifting between Pulse, Crux, and Verbatim never loses the user's place in the book.
  - **Note Crystallization**: Wired the Studio "Crystallize Note" UI button to `POST /api/chapter/crystallize` writing Obsidian-compatible marginalia.
  - **Subtitles & CLI**: Replaced utterance IDs in `.srt` subtitles with actual spoken text, only defaulted to Edge voice when the Edge provider is active, and filtered notes export in `convert --notes` to key passages while preventing duplicate chapter blocks on repeated runs.
  - **Credential Routing**: Built dedicated `AnthropicAdaptProvider` for `api.anthropic.com` with `x-api-key` and `anthropic-version` headers, preventing Anthropic keys from being sent to OpenAI endpoints.
  - **ffmpeg Concat Silence Codec**: Generated silence cushions in matching audio format (MP3 vs WAV) to eliminate concat demuxer stream codec incompatibilities.
  - **Document Ingest Hardening**:
    - EPUB: Filtered by `ebooklib.ITEM_DOCUMENT` and word boundaries so chapters like "discovery", "recovery", and "stock" are never dropped; expanded coverage to `h4`-`h6`, `li`, `pre`, `table`; eliminated duplicate nested tags inside blockquote/aside; extracted cover image into `BookMetadata.cover_image`.
    - PDF: Hardened heading regex with narrative verb exclusion so sentences mentioning chapters or sections do not slice prose paragraphs in half.
    - Markdown / DOCX: Preserved leading indentation for code blocks, and restricted DOCX chapter splits to Heading 1 or short chapter titles.
    - Cleaner & Classifier: Stripped attached citations like `claim[3]` while preserving variable indexing `x[1]`; preserved entity/historical dates like `(Berlin, 1989)` and `(Apple, 1976)`; and fixed markdown list items starting with `* ` being falsely classified as footnotes.
    - Slug Sanitization: Enabled Unicode-aware regex matching for Obsidian and Anki filenames, preserving non-Latin characters (e.g. Japanese, Cyrillic).
