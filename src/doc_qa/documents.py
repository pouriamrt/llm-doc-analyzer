"""Loading and cleaning the source documents."""

from __future__ import annotations

import re
from pathlib import Path

# The upstream spreadsheet export leaks literal NaN cells into the text. Match them as
# whole words only: a plain str.replace("nan", "") also eats maintenance, governance,
# pregnancy, malignancies and unanticipated.
_NAN_CELL = re.compile(r"\bnan\b", re.IGNORECASE)
_BLANK_RUN = re.compile(r"\n{3,}")


def clean_document(text: str) -> str:
    """Strip standalone NaN cells and collapse the blank runs they leave behind."""
    return _BLANK_RUN.sub("\n\n", _NAN_CELL.sub("", text)).strip()


def load_txt_documents(folder: Path) -> dict[str, str]:
    """Map document id (the file stem) to cleaned text, ordered by filename."""
    documents: dict[str, str] = {}
    for path in sorted(folder.glob("*.txt")):
        text = clean_document(path.read_text(encoding="utf-8", errors="replace"))
        if text:
            documents[path.stem] = text
    return documents
