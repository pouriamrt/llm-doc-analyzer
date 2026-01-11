from typing import Dict, List
from pathlib import Path


def load_txt_documents(folder: Path) -> Dict[str, str]:
    docs: Dict[str, str] = {}
    for p in sorted(folder.glob("*.txt")):
        docs[p.stem] = p.read_text(encoding="utf-8", errors="replace")
    return docs


def extract_final_agent_text(events: List[object]) -> str:
    """
    ADK runner yields multiple events; we extract any text parts and concatenate.
    """
    chunks: List[str] = []
    for ev in events:
        content = getattr(ev, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None)
        if not parts:
            continue
        for part in parts:
            txt = getattr(part, "text", None)
            if txt:
                chunks.append(txt)
    return "\n".join(chunks).strip()


def normalize_or_fail_closed(answer: str) -> str:
    """
    No citations required. We still enforce:
    - If the model outputs nothing, fail closed.
    - If it tries to reference external sources, we do not have a perfect detector.
      We rely on the system instruction and a conservative fallback if empty.
    """
    a = (answer or "").strip()
    if not a:
        return "Not found in document."
    return a


def ensure_q_heading(answer: str, q_index: int, q_text: str) -> str:
    """
    If the model forgets the heading, prepend it.
    """
    wanted = f"## Q{q_index}: {q_text}"
    if wanted in answer:
        return answer
    if answer.lstrip().startswith("## "):
        return answer
    return wanted + "\n\n" + answer
