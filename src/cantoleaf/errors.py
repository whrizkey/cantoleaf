import re

# Regex patterns for common API keys
KEY_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"),  # OpenAI
    re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}"),  # Anthropic
    re.compile(r"[a-f0-9]{32}"),  # ElevenLabs / DeepL
]


def redact_secrets(text: str) -> str:
    """Redacts potential API keys from error messages, stack traces, and logs."""
    redacted = text
    for pattern in KEY_PATTERNS:
        redacted = pattern.sub("[REDACTED_API_KEY]", redacted)
    return redacted


class CantoLeafError(Exception):
    """Base exception for all CantoLeaf errors."""

    def __init__(self, message: str) -> None:
        super().__init__(redact_secrets(message))


class ConfigError(CantoLeafError):
    """Raised when configuration or required setting is missing/invalid."""


class IngestError(CantoLeafError):
    """Raised when parsing or cleaning an input document fails."""


class ProviderError(CantoLeafError):
    """Base exception for external and local provider errors."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class BudgetExceededError(CantoLeafError):
    """Raised when cumulative cost exceeds CANTOLEAF_MAX_COST_USD."""


class SynthesisError(CantoLeafError):
    """Raised when speech synthesis or audio processing fails."""
