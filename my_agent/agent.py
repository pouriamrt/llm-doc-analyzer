from google.adk.agents.llm_agent import Agent
from google.adk.runners import InMemoryRunner
import asyncio
from my_agent.prompts import SYSTEM_INSTRUCTION


async def ensure_session_exists(
    runner: InMemoryRunner, app_name: str, user_id: str, session_id: str
) -> None:
    svc = (
        getattr(runner, "session_service", None)
        or getattr(runner, "_session_service", None)
        or getattr(runner, "sessions", None)
    )
    if svc is None:
        raise RuntimeError(
            "InMemoryRunner has no visible session service; cannot create session explicitly."
        )

    create = getattr(svc, "create_session", None)
    if create is None:
        raise RuntimeError("Session service has no create_session method.")

    maybe = create(app_name=app_name, user_id=user_id, session_id=session_id)
    if asyncio.iscoroutine(maybe):
        await maybe


def make_agent(model: str = "gemini-2.5-flash"):
    return Agent(
        model=model,
        name="fullcontext_doc_only_reporter",
        description="Answers questions using only the provided document, in guidance-report style.",
        instruction=SYSTEM_INSTRUCTION,
    )
