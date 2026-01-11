from google.adk.agents.llm_agent import Agent
from my_agent.prompts import SYSTEM_INSTRUCTION


def make_agent(model: str = "gemini-2.5-flash"):
    return Agent(
        model=model,
        name="fullcontext_doc_only_reporter",
        description="Answers questions using only the provided document, in guidance-report style.",
        instruction=SYSTEM_INSTRUCTION,
    )
