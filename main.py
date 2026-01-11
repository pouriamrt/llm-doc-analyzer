from google.adk.runners import InMemoryRunner
from google.genai import types

from my_agent.prompts import QUESTIONS, build_user_prompt
from my_agent.agent import make_agent, ensure_session_exists

import asyncio
from tqdm import tqdm
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


async def answer_one_question(
    runner: InMemoryRunner,
    doc_id: str,
    session_id: str,
    user_id: str,
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

    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    events = []
    async for ev in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=msg,
    ):
        events.append(ev)

    answer = extract_final_agent_text(events)
    answer = normalize_or_fail_closed(answer)
    answer = ensure_q_heading(answer, q_index=q_index, q_text=q_text)
    return answer


async def answer_document(
    doc_id: str,
    document_text: str,
    out_folder: Path,
    model: str = "gemini-2.5-flash",
) -> Path:
    session_id = f"session_{doc_id}"

    app_name = "doc_qa_fullcontext_async"
    user_id = os.getenv("USER_ID", "local_user")

    agent = make_agent(model=model)
    runner = InMemoryRunner(agent=agent, app_name=app_name)

    await ensure_session_exists(
        runner, app_name=app_name, user_id=user_id, session_id=session_id
    )

    report_parts: List[str] = []
    report_parts.append(f"# Best-practice guidance report\n\n## Document: {doc_id}\n")

    with tqdm(
        total=len(QUESTIONS),
        desc=f"Questions [{doc_id}]",
        leave=False,
    ) as qbar:
        for i, q in enumerate(QUESTIONS, start=1):
            ans = await answer_one_question(
                runner,
                doc_id,
                session_id,
                user_id,
                i,
                q,
                document_text,
            )
            report_parts.append(ans)
            report_parts.append("\n")
            qbar.update(1)

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

    # Concurrency across documents (questions remain sequential per document)
    max_concurrency = int(os.getenv("MAX_CONCURRENCY", "3"))
    sem = asyncio.Semaphore(max_concurrency)

    async def sem_task(doc_id: str, text: str):
        async with sem:
            return await answer_document(doc_id, text, out_dir, model)

    tasks = [
        asyncio.create_task(sem_task(doc_id, text)) for doc_id, text in docs.items()
    ]
    results = await asyncio.gather(*tasks)

    for p in results:
        print(f"Wrote: {p.resolve()}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
