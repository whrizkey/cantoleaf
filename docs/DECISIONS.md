# Architecture Decision Records (ADR)

## ADR-001: Multi-Rail Cognitive Audio Graph
- **Context**: Existing readers stream text strictly line-by-line. Listeners cannot shift density without losing temporal position.
- **Decision**: Every utterance across `Pulse`, `Crux`, and `Verbatim` shares a canonical `block_index` derived from the source AST. Mid-chapter gearshifts seamlessly jump to the corresponding paragraph.
- **Consequences**: Enables interactive density switching and accurate marginalia citations back to source paragraphs.

## ADR-002: Content-Addressed SQLite WAL Audio Cache
- **Context**: Re-reading or switching between gears could cause expensive re-synthesis calls to cloud providers.
- **Decision**: Cache keys combine `SHA256(text, provider, voice, rate, block_kind, enable_earcons)` stored in SQLite with WAL mode.
- **Consequences**: Zero duplicate API calls, instant offline replay, and robust multi-process concurrency.

## ADR-003: Procedural Earcons & Sonic Typography
- **Context**: Spoken cues ("Chapter 1", "Quote", "End quote") clutter listening and break immersion.
- **Decision**: Synthesize mathematical harmonic micro-chimes and plucks using `numpy` at the sample rate of the audio file.
- **Consequences**: Zero external audio asset dependencies; instant procedural generation.

## ADR-004: Hard Circuit Breaker Spend Protection
- **Context**: Using BYOK cloud TTS (ElevenLabs, OpenAI) on large books risks high cloud bills.
- **Decision**: `UsageTracker` reads unit costs from `pricing.toml` and validates character usage before every remote synthesis. If `CANTOLEAF_MAX_COST_USD` is reached, it raises `BudgetExceededError`.
- **Consequences**: Guaranteed bill cap; prevents unexpected credit depletion.

## ADR-005: Exact Pause Cushioning in Concat Demuxer
- **Context**: When `.lrc` and `.srt` files incorporate `pause_after_sec` into timestamp offsets, audio files must contain matching silence buffers or drift occurs.
- **Decision**: Master `.m4b` concatenates exact WAV silence cushions matching `pause_after_sec` (including 4-second recall tick pulses for Socratic Memory Locks).
- **Consequences**: Subtitle highlighting and audio playback stay in frame-accurate synchronization.
