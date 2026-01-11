from google.adk.runners import InMemoryRunner

from my_agent.prompts import QUESTIONS, build_user_prompt
from my_agent.agent import make_agent

import asyncio
from pathlib import Path
from typing import List
import os

from dotenv import load_dotenv

from utils import (
    load_txt_documents,
    extract_final_agent_text,
    normalize_or_fail_closed,
    ensure_q_heading,
)


def answer_one_question_sync(
    runner: InMemoryRunner,
    doc_id: str,
    session_id: str,
    q_index: int,
    q_text: str,
    document_text: str,
) -> str:
    prompt = build_user_prompt(
        doc_id=doc_id,
        question_index=q_index,
        question_text=q_text,
        document_text=document_text,
    )

    events = list(
        runner.run(
            user_id="local_user",
            session_id=session_id,
            new_message=prompt,
        )
    )

    answer = extract_final_agent_text(events)
    answer = normalize_or_fail_closed(answer)
    answer = ensure_q_heading(answer, q_index=q_index, q_text=q_text)
    return answer


async def answer_document(
    runner: InMemoryRunner,
    doc_id: str,
    document_text: str,
    out_folder: Path,
) -> Path:
    """
    For one document: ask questions sequentially (for depth and focus),
    but run the whole doc pipeline inside a thread (runner is sync).
    """
    session_id = f"session_{doc_id}"

    report_parts: List[str] = []
    report_parts.append(f"# Best-practice guidance report\n\n## Document: {doc_id}\n")

    for i, q in enumerate(QUESTIONS, start=1):
        # Run sync ADK call in a worker thread so we can process multiple docs concurrently.
        ans = await asyncio.to_thread(
            answer_one_question_sync,
            runner,
            doc_id,
            session_id,
            i,
            q,
            document_text,
        )
        report_parts.append(ans)
        report_parts.append("\n")

    out_path = out_folder / f"{doc_id}_report.md"
    out_path.write_text("\n".join(report_parts).strip() + "\n", encoding="utf-8")
    return out_path


async def main() -> None:
    load_dotenv()

    docs_dir = Path(os.getenv("DOCS_DIR", "data"))
    out_dir = Path(os.getenv("OUT_DIR", "data/outputs"))
    out_dir.mkdir(parents=True, exist_ok=True)

    model = os.getenv("ADK_MODEL", "gemini-2.5-flash")

    docs = load_txt_documents(docs_dir)
    if not docs:
        raise SystemExit(f"No .txt files found in: {docs_dir.resolve()}")

    agent = make_agent(model=model)
    runner = InMemoryRunner(agent=agent, app_name="doc_qa_fullcontext_async")

    # Concurrency across documents (questions remain sequential per document)
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "3"))
    sem = asyncio.Semaphore(max_concurrency)

    async def sem_task(doc_id: str, text: str):
        async with sem:
            return await answer_document(runner, doc_id, text, out_dir)

    tasks = [
        asyncio.create_task(sem_task(doc_id, text)) for doc_id, text in docs.items()
    ]
    results = await asyncio.gather(*tasks)

    for p in results:
        print(f"Wrote: {p.resolve()}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
