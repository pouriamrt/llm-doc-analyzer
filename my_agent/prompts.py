QUESTIONS = [
    "1- What is the definition of this practice?",
    "2- Why is this practice beneficial or important?",
    "3- When should this practice be used?",
    "4- When is it justified to not use this practice?",
    "5- How should the correct methods for this practice be selected?",
    "6- How should the correct methods for this practice be implemented?",
    "7- How should the correct methods for this practice be evaluated?",
    "8- If it is justified to not use this practice, then what should be done as an alternative?",
]

SYSTEM_INSTRUCTION = """
You are writing a best-practice guidance report from a single provided document.

Hard rules (non-negotiable):
- Use ONLY the document content provided in the user message.
- Do NOT use outside knowledge, common sense, or assumptions.
- If the document does not explicitly support an answer or subsection, write exactly:
  Not found in document.
- Do not invent definitions, criteria, methods, or recommendations.
- Be long, detailed and hierarchical especially when the document actually contains enough detail.

Writing style (must match):
- Professional guidance-report tone.
- Structured and hierarchical.
- Use clear headings and subheadings.
- Prefer bullet lists with nested bullets where helpful.
- Avoid fluff. Be concrete and procedural when the doc supports it.
- Reuse the following section labels where relevant:
  • Key messages
  • Definition and purpose
  • Why this matters (benefits and importance)
  • When to use
  • When it may be justified not to use (exceptions / constraints)
  • How to select appropriate methods
  • How to implement
  • How to evaluate
  • If not used: alternatives / mitigation steps

Output formatting rules:
- Output MUST be valid Markdown.
- For each question, start with a level-2 heading: "## Q<N>: <question text>"
""".strip()


def build_user_prompt(
    doc_id: str, question_index: int, question_text: str, document_text: str
) -> str:
    return f"""
Document ID: {doc_id}

You will answer ONE question using ONLY the document below.

Question:
{question_text}

Requirements for this question:
- Start with: "## Q{question_index}: {question_text}"
- Then write the answer to the question, unless "Not found in document."
- Then include the most relevant subsections from the allowed labels list.
- If a subsection is not supported by the document, write: Not found in document.

Allowed subsection labels (use only those that fit this question):
- Key messages
- Definition and purpose
- Why this matters (benefits and importance)
- When to use
- When it may be justified not to use (exceptions / constraints)
- How to select appropriate methods
- How to implement
- How to evaluate
- If not used: alternatives / mitigation steps

Document:
<<<BEGIN DOCUMENT
{document_text.replace("nan", "")}
END DOCUMENT>>>
""".strip()
