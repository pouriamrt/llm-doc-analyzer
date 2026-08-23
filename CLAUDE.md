# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Project overview

Doc QA is an async document analysis pipeline built on Google ADK. It answers eight fixed
questions per document using only that document's content, and fails closed with
`Not found in document.` when the text does not support an answer.

## Commands

```bash
uv sync --all-groups        # install runtime + dev tooling
uv run doc-qa run           # run the pipeline
uv run doc-qa list-docs     # list documents that would be processed
uv run doc-qa run --dry-run # plan only, no model calls

uv run ruff check --fix .   # lint
uv run ruff format .        # format
uv run mypy                 # strict type check (src only)
uv run pytest               # tests, 80% coverage floor
```

CLI flags override environment variables, which override `.env`, which override defaults.

## Configuration

`.env` in the project root; `.env.example` lists every variable. `ADK_MODEL` defaults to
`openai/gpt-5.6-terra`. Only the API key matching the chosen provider is required, and it
is validated at startup.

## Architecture

```
cli.run
 └─ run_pipeline          documents concurrent, bounded by asyncio.Semaphore
     └─ answer_document   one ADK session per document
         └─ ask x8        one turn per question, no retry at this level
```

- **src/doc_qa/cli.py** — Typer app, settings assembly, exit codes.
- **src/doc_qa/config.py** — `Settings` (pydantic-settings), credential export, structlog setup.
- **src/doc_qa/pipeline.py** — orchestration, retry policy, per-document error isolation.
- **src/doc_qa/agent.py** — `resolve_model`, `make_agent`, `make_runner`.
- **src/doc_qa/prompts.py** — questions, system instruction, first and follow-up builders.
- **src/doc_qa/documents.py** — loading and cleaning.
- **src/doc_qa/parsing.py** — ADK events to Markdown.

## Invariants worth preserving

- **The document is sent once per document.** `build_first_prompt` carries it; the seven
  follow-up turns carry only the question. `tests/test_pipeline.py` asserts this; if that
  test fails, input token cost has silently risen eightfold.
- **`resolve_model` decides by the `/` in the model name.** `Agent(model=...)` accepts a
  bare string only for Gemini. Every other provider needs a `LiteLlm` instance, so passing
  a LiteLLM string through unwrapped fails at the registry lookup.
- **`Settings.export_provider_credentials` must be called before any model call.** LiteLLM
  and google-genai read keys from `os.environ`, not from the `Settings` object.
- **NaN cleaning is word-boundary anchored.** A substring replace corrupts `maintenance`,
  `governance`, `pregnancy`, `malignancies` and `unanticipated`, all of which appear in the
  corpus.
- **A failing document must not abort the batch.** `run_pipeline` catches per document and
  returns a `FAILED` result rather than letting `gather` cancel its siblings.
- **Retries live at the document level, never the turn level.** ADK commits the user
  message to the session before the model runs (`Runner._append_user_event`), so a rate
  limit lands after the turn is already in the history. Retrying a turn would append it
  twice; `answer_document` retries the whole document with a fresh runner and session.
- **`require_credentials` is called by `run`, not by the validator.** `list-docs` reaches
  no model and must work with no provider key configured.
- **Fail closed.** Empty model output becomes `Not found in document.`, never an empty section.

## ADK notes

Pinned to `google-adk >= 2.7.1`. In 2.x, `Runner` exposes `session_service` publicly and
accepts `auto_create_session=True`, which is why no session is created by hand. ADK's own
`RetryConfig` binds to workflow graph nodes, not to an `LlmAgent` driven by a `Runner`, so
retries live in `pipeline.answer_document` via tenacity, at the document level for the
reason given in the invariants above.

## Code style

Python 3.13+, fully async, `from __future__ import annotations`, builtin generics. Ruff for
lint and format, mypy strict over `src`. Tests never hit the network — a stub runner in
`tests/conftest.py` stands in for the ADK `Runner`.
