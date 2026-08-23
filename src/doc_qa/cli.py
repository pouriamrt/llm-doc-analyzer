"""Command line entry point."""

from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path
from typing import Annotated

import structlog
import typer

from doc_qa.config import LogLevel, Settings, configure_logging
from doc_qa.documents import load_txt_documents
from doc_qa.pipeline import DocumentResult, NoDocumentsError, Status, run_pipeline

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Generate best-practice guidance reports from text documents.",
)
log = structlog.get_logger(__name__)

ModelOpt = Annotated[str | None, typer.Option("--model", help="Override ADK_MODEL.")]
DocsOpt = Annotated[Path | None, typer.Option("--docs-dir", help="Override DOCS_DIR.")]
OutOpt = Annotated[Path | None, typer.Option("--out-dir", help="Override OUT_DIR.")]
ConcOpt = Annotated[int | None, typer.Option("--concurrency", help="Override MAX_CONCURRENCY.")]
OverwriteOpt = Annotated[
    bool | None, typer.Option("--overwrite/--no-overwrite", help="Regenerate existing reports.")
]
LogOpt = Annotated[LogLevel | None, typer.Option("--log-level", help="Override LOG_LEVEL.")]
DryRunOpt = Annotated[
    bool, typer.Option("--dry-run", help="Show the plan without calling the model.")
]


def _build_settings(**overrides: object) -> Settings:
    """CLI flags beat environment, which beats .env, which beats defaults."""
    supplied = {key: value for key, value in overrides.items() if value is not None}
    settings = Settings(**supplied)  # type: ignore[arg-type]
    settings.export_provider_credentials()
    return settings


@app.command()
def run(
    model: ModelOpt = None,
    docs_dir: DocsOpt = None,
    out_dir: OutOpt = None,
    concurrency: ConcOpt = None,
    overwrite: OverwriteOpt = None,
    log_level: LogOpt = None,
    dry_run: DryRunOpt = False,
) -> None:
    """Answer every question for every document and write the reports."""
    try:
        settings = _build_settings(
            adk_model=model,
            docs_dir=docs_dir,
            out_dir=out_dir,
            max_concurrency=concurrency,
            overwrite=overwrite,
            log_level=log_level,
        )
        # `run` reaches the model, so demand the key now rather than mid-batch.
        # `list-docs` never does, and deliberately does not call this.
        settings.require_credentials()
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    configure_logging(settings.log_level)

    if dry_run:
        documents = load_txt_documents(settings.docs_dir)
        log.info(
            "dry run",
            model=settings.adk_model,
            documents=len(documents),
            out_dir=str(settings.out_dir),
            concurrency=settings.max_concurrency,
            overwrite=settings.overwrite,
        )
        return

    log.info("starting", model=settings.adk_model, concurrency=settings.max_concurrency)
    try:
        results = asyncio.run(run_pipeline(settings))
    except NoDocumentsError as exc:
        raise typer.BadParameter(str(exc)) from exc

    _report(results)


@app.command("list-docs")
def list_docs(docs_dir: DocsOpt = None) -> None:
    """List the documents that would be processed."""
    settings = _build_settings(docs_dir=docs_dir)
    documents = load_txt_documents(settings.docs_dir)
    for doc_id, text in documents.items():
        typer.echo(f"{doc_id}\t{len(text):,} chars")
    typer.echo(f"{len(documents)} document(s) in {settings.docs_dir}")


def _report(results: list[DocumentResult]) -> None:
    """Print a per-status summary and exit non-zero if anything failed."""
    counts = Counter(result.status for result in results)
    for result in results:
        if result.status is Status.FAILED:
            typer.echo(f"FAILED  {result.doc_id}: {result.error}", err=True)
    summary = "  ".join(f"{status.value}={counts[status]}" for status in Status)
    typer.echo(f"Done. {summary}")
    if counts[Status.FAILED]:
        raise typer.Exit(code=1)


if __name__ == "__main__":  # pragma: no cover
    app()
