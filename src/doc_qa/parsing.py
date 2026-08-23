"""Turning ADK events into report-ready Markdown."""

from __future__ import annotations

from collections.abc import Iterable

from google.adk.events import Event

from doc_qa.prompts import NOT_FOUND


def extract_final_agent_text(events: Iterable[Event]) -> str:
    """Text of the agent's final response, ignoring partial and tool-call events."""
    chunks = [
        part.text
        for event in events
        if event.is_final_response() and event.content and event.content.parts
        for part in event.content.parts
        if part.text
    ]
    return "\n".join(chunks).strip()


def normalize_or_fail_closed(answer: str) -> str:
    """An empty model response must never become an empty report section."""
    return answer.strip() or NOT_FOUND


def ensure_q_heading(answer: str, question_index: int, question_text: str) -> str:
    """Prepend the required heading when the model omits it."""
    if answer.lstrip().startswith(f"## Q{question_index}"):
        return answer
    return f"## Q{question_index}: {question_text}\n\n{answer}"
