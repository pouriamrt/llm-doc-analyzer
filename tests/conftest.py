"""Shared fixtures. No test in this suite touches the network."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import structlog
from google.adk.events import Event
from google.genai import types

from doc_qa.config import Settings

MARKER = "END DOCUMENT>>>"


def make_event(text: str, *, partial: bool = False) -> Event:
    return Event(
        author="agent",
        partial=partial,
        content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


class StubRunner:
    """Stands in for adk Runner: records prompts, yields canned events."""

    def __init__(
        self,
        reply: str = "stub answer",
        fail_with: Exception | None = None,
        close_error: Exception | None = None,
    ) -> None:
        self.prompts: list[str] = []
        self.reply = reply
        self.fail_with = fail_with
        self.close_error = close_error
        self.closed = False

    async def run_async(
        self, *, user_id: str, session_id: str, new_message: types.Content
    ) -> AsyncIterator[Event]:
        self.prompts.append(new_message.parts[0].text or "")
        if self.fail_with is not None:
            raise self.fail_with
        yield make_event(f"{self.reply} ({len(self.prompts)})")

    async def close(self) -> None:
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


@pytest.fixture(autouse=True)
def _silence_logging() -> None:
    """Structlog writes nowhere during tests; pytest owns the streams."""
    structlog.configure(
        processors=[],
        logger_factory=structlog.ReturnLoggerFactory(),
        cache_logger_on_first_use=False,
    )


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    docs = tmp_path / "docs"
    docs.mkdir()
    return Settings(
        _env_file=None,
        adk_model="openai/gpt-5.6-terra",
        docs_dir=docs,
        out_dir=tmp_path / "out",
        max_concurrency=2,
        overwrite=True,
        max_attempts=1,
    )
