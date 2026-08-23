import pytest
from litellm.exceptions import RateLimitError
from tenacity import wait_none

from conftest import MARKER, StubRunner
from doc_qa.pipeline import (
    DocumentResult,
    NoDocumentsError,
    Status,
    answer_document,
    run_pipeline,
)
from doc_qa.prompts import QUESTIONS


@pytest.fixture
def stub(monkeypatch):
    runner = StubRunner()
    monkeypatch.setattr("doc_qa.pipeline.make_agent", lambda model: object())
    monkeypatch.setattr("doc_qa.pipeline.make_runner", lambda agent: runner)
    return runner


async def test_document_is_sent_exactly_once(stub, settings):
    """The whole point of the session-reuse design: 8 turns, 1 copy of the document."""
    settings.out_dir.mkdir(parents=True)

    await answer_document("doc1", "BODY TEXT", settings)

    assert len(stub.prompts) == len(QUESTIONS) == 8
    assert sum(MARKER in prompt for prompt in stub.prompts) == 1
    assert "BODY TEXT" in stub.prompts[0]
    assert all("BODY TEXT" not in prompt for prompt in stub.prompts[1:])


async def test_report_has_a_heading_per_question(stub, settings):
    settings.out_dir.mkdir(parents=True)

    result = await answer_document("doc1", "BODY", settings)

    report = result.path.read_text(encoding="utf-8")
    assert result.status is Status.WRITTEN
    assert stub.closed
    for index in range(1, len(QUESTIONS) + 1):
        assert f"## Q{index}:" in report


async def test_existing_report_is_skipped_without_calling_the_model(stub, settings):
    settings.out_dir.mkdir(parents=True)
    (settings.out_dir / "doc1_report.md").write_text("old", encoding="utf-8")
    settings.overwrite = False

    result = await answer_document("doc1", "BODY", settings)

    assert result.status is Status.SKIPPED
    assert stub.prompts == []
    assert (settings.out_dir / "doc1_report.md").read_text(encoding="utf-8") == "old"


async def test_empty_docs_dir_raises(settings):
    with pytest.raises(NoDocumentsError):
        await run_pipeline(settings)


async def test_one_failing_document_does_not_discard_the_batch(monkeypatch, settings):
    (settings.docs_dir / "good.txt").write_text("fine", encoding="utf-8")
    (settings.docs_dir / "bad.txt").write_text("boom", encoding="utf-8")

    def runner_for(agent):
        # The failing document is decided by call order; both runners are distinct.
        return runners.pop(0)

    runners = [
        StubRunner(fail_with=RateLimitError("429", llm_provider="openai", model="x")),
        StubRunner(),
    ]
    monkeypatch.setattr("doc_qa.pipeline.make_agent", lambda model: object())
    monkeypatch.setattr("doc_qa.pipeline.make_runner", runner_for)
    settings.max_concurrency = 1

    results: list[DocumentResult] = await run_pipeline(settings)

    by_status = {result.doc_id: result.status for result in results}
    assert len(results) == 2
    assert Status.FAILED in by_status.values()
    assert Status.WRITTEN in by_status.values()


def _rate_limit() -> RateLimitError:
    return RateLimitError("429", llm_provider="openai", model="x")


async def test_transient_failure_retries_the_whole_document_with_a_fresh_session(
    monkeypatch, settings
):
    """ADK commits the user turn before the model runs, so a retried turn would be
    appended twice. Retrying the document instead must rebuild runner and session."""
    created: list[StubRunner] = []

    def make(agent):
        runner = StubRunner(fail_with=_rate_limit()) if not created else StubRunner()
        created.append(runner)
        return runner

    monkeypatch.setattr("doc_qa.pipeline.make_agent", lambda model: object())
    monkeypatch.setattr("doc_qa.pipeline.make_runner", make)
    monkeypatch.setattr("doc_qa.pipeline.wait_exponential_jitter", lambda **kw: wait_none())
    settings.max_attempts = 2
    settings.out_dir.mkdir(parents=True)

    result = await answer_document("doc1", "BODY TEXT", settings)

    assert result.status is Status.WRITTEN
    assert len(created) == 2, "retry must build a fresh runner, not reuse the poisoned one"
    assert len(created[1].prompts) == len(QUESTIONS)
    assert sum(MARKER in prompt for prompt in created[1].prompts) == 1


async def test_close_failure_does_not_mask_the_real_error(monkeypatch, settings):
    runner = StubRunner(fail_with=ValueError("real cause"), close_error=OSError("close blew up"))
    monkeypatch.setattr("doc_qa.pipeline.make_agent", lambda model: object())
    monkeypatch.setattr("doc_qa.pipeline.make_runner", lambda agent: runner)
    settings.out_dir.mkdir(parents=True)

    with pytest.raises(ValueError, match="real cause"):
        await answer_document("doc1", "BODY", settings)

    assert runner.closed
