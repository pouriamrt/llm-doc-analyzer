# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Doc QA is an async document analysis pipeline that uses Google ADK (Agent Development Kit) to generate structured best-practice guidance reports from text documents. It answers 8 predefined questions per document using only the document's content (fail-closed: outputs "Not found in document." when unsupported).

## Commands

```bash
# Install dependencies
uv sync

# Run the pipeline
python main.py

# Lint and format (via pre-commit)
pre-commit run --all-files

# Lint only
ruff check --fix .

# Format only
ruff format .
```

There are no tests in this project currently.

## Environment Configuration

All configuration is via `.env` in the project root. Key variables:

- `ADK_MODEL` - Model identifier (default: `gemini-2.5-flash`). Supports LiteLLM model strings like `openai/gpt-5.2`.
- `DOCS_DIR` / `OUT_DIR` - Input/output directories (default: `data` / `data/outputs`)
- `MAX_CONCURRENCY` - Parallel document limit (default: `3`)
- `OVERWRITE` - Whether to regenerate existing reports (default: `True`)
- `GOOGLE_API_KEY` - Required for Gemini models
- `GOOGLE_GENAI_USE_VERTEXAI` - Set to `0` for direct API access

## Architecture

### Processing Pipeline

```
main.py:main() → loads .txt docs → spawns concurrent tasks (semaphore-bounded)
  └─ answer_document() → creates ADK agent + runner + session per document
       └─ answer_one_question() × 8 (sequential per document)
            └─ build_user_prompt() → runner.run_async() → extract/normalize/heading
```

Documents are processed concurrently; the 8 questions within each document are processed sequentially to maintain conversational session state.

### Module Responsibilities

- **main.py** - Entry point, orchestration, async concurrency control with `asyncio.Semaphore`
- **my_agent/agent.py** - `make_agent()` factory and `ensure_session_exists()` which handles ADK session service discovery via attribute probing (`session_service`, `_session_service`, `sessions`)
- **my_agent/prompts.py** - `SYSTEM_INSTRUCTION`, `QUESTIONS` list, and `build_user_prompt()` template. The system instruction enforces document-only responses with specific allowed subsection labels.
- **utils.py** - Document I/O (`load_txt_documents`), ADK event parsing (`extract_final_agent_text`), response validation (`normalize_or_fail_closed`), and heading enforcement (`ensure_q_heading`)

### Key Design Decisions

- **Fail-closed**: Empty model responses become "Not found in document." — never hallucinate.
- **Session per document**: Each document gets its own ADK InMemoryRunner session so question context accumulates within a single document but doesn't leak across documents.
- **Model flexibility**: The `ADK_MODEL` env var accepts both native Gemini model names and LiteLLM-prefixed strings (e.g., `openai/gpt-5.2`), with `LiteLlm` wrapper imported but model selection handled at runtime.
- **Overwrite control**: When `OVERWRITE=False`, existing `{doc_id}_report.md` files are skipped entirely (no API calls made).

## Code Style

- Python 3.13+, fully async
- Ruff for linting and formatting (configured via pre-commit, Ruff v0.14.4)
- Type hints used throughout (`Dict`, `List`, `Path`, `tuple`)
