import os

import pytest
from pydantic import ValidationError

from doc_qa.config import Settings


def test_overwrite_false_string_is_parsed_as_bool(monkeypatch):
    monkeypatch.setenv("OVERWRITE", "False")
    assert Settings(_env_file=None).overwrite is False


def test_settings_build_without_any_credentials(monkeypatch):
    """Construction must not demand a key: `list-docs` never reaches the model."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert Settings(_env_file=None, adk_model="openai/gpt-5.6-terra").provider == "openai"


def test_require_credentials_rejects_missing_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(_env_file=None, adk_model="openai/gpt-5.6-terra")

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        settings.require_credentials()


def test_require_credentials_rejects_missing_google_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    settings = Settings(_env_file=None, adk_model="gemini-2.5-flash")

    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        settings.require_credentials()


def test_require_credentials_passes_for_unknown_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = Settings(_env_file=None, adk_model="ollama/llama4")

    settings.require_credentials()  # providers we do not model manage their own keys

    assert settings.provider == "ollama"


def test_credentials_are_exported_to_process_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    settings = Settings(_env_file=None, adk_model="openai/gpt-5.6-terra", openai_api_key="secret")

    settings.export_provider_credentials()

    # LiteLLM reads the process env, not the Settings object.
    assert os.environ["OPENAI_API_KEY"] == "secret"
    assert os.environ["GOOGLE_GENAI_USE_VERTEXAI"] == "0"


def test_export_overwrites_a_stale_environment_value(monkeypatch):
    """setdefault would leave the old key in place and silently use the wrong account."""
    monkeypatch.setenv("OPENAI_API_KEY", "stale")
    settings = Settings(_env_file=None, adk_model="openai/gpt-5.6-terra", openai_api_key="fresh")

    settings.export_provider_credentials()

    assert os.environ["OPENAI_API_KEY"] == "fresh"


def test_concurrency_is_bounded():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_concurrency=0)
