"""Agent and runner construction."""

from __future__ import annotations

from google.adk.agents.llm_agent import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from doc_qa.prompts import SYSTEM_INSTRUCTION

APP_NAME = "doc_qa"


def resolve_model(name: str) -> str | BaseLlm:
    """Provider-prefixed names need a LiteLlm wrapper; bare names hit ADK's Gemini registry.

    `Agent(model=...)` is polymorphic — the type carries the routing decision, so a
    LiteLLM string passed through as `str` would be looked up as a Gemini model and fail.
    """
    return LiteLlm(model=name) if "/" in name else name


def make_agent(model: str) -> Agent:
    return Agent(
        model=resolve_model(model),
        name="fullcontext_doc_only_reporter",
        description=(
            "Answers questions using only the provided document, in guidance-report style."
        ),
        instruction=SYSTEM_INSTRUCTION,
    )


def make_runner(agent: Agent, app_name: str = APP_NAME) -> Runner:
    """auto_create_session (ADK 2.x) removes the need to pre-create sessions by hand."""
    return Runner(
        app_name=app_name,
        agent=agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
