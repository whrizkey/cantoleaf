from cantoleaf.errors import CantoLeafError, redact_secrets


def test_redact_openai_key() -> None:
    msg = "Error connecting with key sk-1234567890abcdef1234567890abcdef to OpenAI"
    clean = redact_secrets(msg)
    assert "sk-1234567890abcdef" not in clean
    assert "[REDACTED_API_KEY]" in clean


def test_cantoleaf_error_redacts_message() -> None:
    err = CantoLeafError("Unauthorized key: sk-ant-api03-123456789012345678901234")
    assert "sk-ant" not in str(err)
    assert "[REDACTED_API_KEY]" in str(err)
