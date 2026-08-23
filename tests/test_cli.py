from typer.testing import CliRunner

from doc_qa.cli import app

runner = CliRunner()


def test_list_docs(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    (tmp_path / "one.txt").write_text("maintenance", encoding="utf-8")

    result = runner.invoke(app, ["list-docs", "--docs-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert "one" in result.stdout
    assert "1 document(s)" in result.stdout


def test_dry_run_makes_no_model_call(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    (tmp_path / "one.txt").write_text("body", encoding="utf-8")

    result = runner.invoke(
        app,
        ["run", "--dry-run", "--docs-dir", str(tmp_path), "--out-dir", str(tmp_path / "o")],
    )

    assert result.exit_code == 0


def test_missing_credentials_is_a_clean_error(tmp_path, monkeypatch):
    # Isolate from the repository's own .env, which legitimately supplies the key.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / "docs").mkdir()

    result = runner.invoke(app, ["run", "--model", "openai/gpt-5.6-terra", "--docs-dir", "docs"])

    assert result.exit_code != 0
    assert "OPENAI_API_KEY" in " ".join(result.output.split())


def test_empty_docs_dir_is_a_clean_error(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    (tmp_path / "docs").mkdir()

    result = runner.invoke(app, ["run", "--docs-dir", str(tmp_path / "docs")])

    assert result.exit_code != 0
    assert "No .txt files found" in " ".join(result.output.split())


def test_list_docs_works_without_credentials(tmp_path, monkeypatch):
    """Listing files reaches no model, so it must not demand a provider key."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "one.txt").write_text("body", encoding="utf-8")

    result = runner.invoke(app, ["list-docs", "--docs-dir", "docs"])

    assert result.exit_code == 0, result.output
    assert "1 document(s)" in result.stdout
