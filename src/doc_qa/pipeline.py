"""Orchestration: one question, one document, one run."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import structlog
from google.adk.runners import Runner
from google.genai import types
from google.genai.errors import ServerError
from litellm.exceptions import (
    APIConnectionError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)
from tqdm.asyncio import tqdm as tqdm_asyncio

from doc_qa.agent import make_agent, make_runner
from doc_qa.config import Settings
from doc_qa.documents import load_txt_documents
from doc_qa.parsing import ensure_q_heading, extract_final_agent_text, normalize_or_fail_closed
from doc_qa.prompts import QUESTIONS, build_first_prompt, build_followup_prompt

log = structlog.get_logger(__name__)

# Retried with backoff. Anything else (auth, bad request, bad model name) is permanent
# and should surface immediately rather than after five slow attempts.
TRANSIENT_ERRORS = (
    APIConnectionError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
    ServerError,
)


def report_path(settings: Settings, doc_id: str) -> Path:
    """Single definition of the output naming convention."""
    return settings.out_dir / f"{doc_id}_report.md"


class NoDocumentsError(RuntimeError):
    """Raised when the input directory holds no usable .txt files."""


class Status(StrEnum):
    WRITTEN = "written"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DocumentResult:
    doc_id: str
    path: Path
    status: Status
    error: str | None = None


async def ask(
    runner: Runner,
    *,
    user_id: str,
    session_id: str,
    prompt: str,
) -> str:
    """Send one turn and return the agent's final text.

    Deliberately has no retry of its own. ADK commits the user message to the session
    before the model runs (`Runner._append_user_event`), so a rate limit — which lands
    before generation starts — leaves the turn already in the history. Re-sending the
    same message would append it twice and corrupt the rest of the conversation.
    Retries therefore live one level up, where a fresh session is built.
    """
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    events = [
        event
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        )
    ]
    return extract_final_agent_text(events)


async def generate_report(doc_id: str, document_text: str, settings: Settings) -> str:
    """Answer every question in one fresh session and return the report body."""
    runner = make_runner(make_agent(settings.adk_model))
    session_id = f"session_{doc_id}"
    parts: list[str] = [f"# Best-practice guidance report\n\n## Document: {doc_id}\n"]

    try:
        for index, question in enumerate(QUESTIONS, start=1):
            prompt = (
                build_first_prompt(doc_id, index, question, document_text)
                if index == 1
                else build_followup_prompt(index, question)
            )
            raw = await ask(runner, user_id=settings.user_id, session_id=session_id, prompt=prompt)
            answer = ensure_q_heading(normalize_or_fail_closed(raw), index, question)
            parts.extend((answer, ""))
            log.debug("question answered", question=index, chars=len(answer))
    finally:
        try:
            await runner.close()
        except Exception as exc:  # never let cleanup replace the real failure
            log.warning("runner close failed", error=str(exc))

    return "\n".join(parts).strip() + "\n"


async def answer_document(doc_id: str, document_text: str, settings: Settings) -> DocumentResult:
    """Produce one document's report, retrying the whole document on transient failures.

    The document is sent once per attempt, in the first turn; the other seven turns
    carry only the question, because the session already holds the text.
    """
    out_path = report_path(settings, doc_id)
    if out_path.exists() and not settings.overwrite:
        log.info("skipped, report already exists")
        return DocumentResult(doc_id, out_path, Status.SKIPPED)

    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(settings.max_attempts),
        wait=wait_exponential_jitter(initial=2, max=60),
        retry=retry_if_exception_type(TRANSIENT_ERRORS),
        reraise=True,
    ):
        with attempt:
            report = await generate_report(doc_id, document_text, settings)
            out_path.write_text(report, encoding="utf-8")
            log.info("report written", path=str(out_path))
            return DocumentResult(doc_id, out_path, Status.WRITTEN)
    raise AssertionError("unreachable: AsyncRetrying always returns or raises")


async def run_pipeline(settings: Settings) -> list[DocumentResult]:
    """Process every document concurrently, isolating per-document failures."""
    documents = load_txt_documents(settings.docs_dir)
    if not documents:
        msg = f"No .txt files found in: {settings.docs_dir.resolve()}"
        raise NoDocumentsError(msg)

    settings.out_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(settings.max_concurrency)

    async def guarded(doc_id: str, text: str) -> DocumentResult:
        async with semaphore:
            structlog.contextvars.bind_contextvars(doc_id=doc_id)
            try:
                return await answer_document(doc_id, text, settings)
            except Exception as exc:  # one bad document must not discard the batch
                # asyncio.CancelledError is a BaseException and is not caught here.
                log.error("document failed", error=str(exc), error_type=type(exc).__name__)
                return DocumentResult(
                    doc_id, report_path(settings, doc_id), Status.FAILED, str(exc)
                )
            finally:
                structlog.contextvars.clear_contextvars()

    tasks = [guarded(doc_id, text) for doc_id, text in documents.items()]
    results: list[DocumentResult] = await tqdm_asyncio.gather(
        *tasks, desc="Documents", file=sys.stderr
    )
    return results
