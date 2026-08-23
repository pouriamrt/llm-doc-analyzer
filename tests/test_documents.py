from pathlib import Path

import pytest

from doc_qa.documents import clean_document, load_txt_documents

# Every one of these was silently mangled by the old str.replace("nan", "") hack.
SURVIVES = ["maintenance", "governance", "pregnancy", "malignancies", "unanticipated", "resonance"]


@pytest.mark.parametrize("word", SURVIVES)
def test_words_containing_nan_survive(word):
    assert clean_document(f"The {word} phase matters.") == f"The {word} phase matters."


@pytest.mark.parametrize("cell", ["nan", "NaN", "NAN", "Nan"])
def test_standalone_nan_cells_are_stripped(cell):
    assert cell.lower() not in clean_document(f"Outcome: {cell} reported").lower()


def test_blank_runs_are_collapsed():
    assert clean_document("a\n\nnan\n\nnan\n\nb") == "a\n\nb"


def test_loader_reads_sorted_stems_and_cleans(tmp_path: Path):
    (tmp_path / "b.txt").write_text("second nan doc", encoding="utf-8")
    (tmp_path / "a.txt").write_text("maintenance plan", encoding="utf-8")
    (tmp_path / "empty.txt").write_text("   nan  ", encoding="utf-8")
    (tmp_path / "ignored.md").write_text("not a txt", encoding="utf-8")

    docs = load_txt_documents(tmp_path)

    assert list(docs) == ["a", "b"]  # sorted, empty-after-cleaning dropped
    assert docs["a"] == "maintenance plan"
    assert "nan" not in docs["b"]
