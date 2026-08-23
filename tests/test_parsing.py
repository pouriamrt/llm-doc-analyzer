from conftest import make_event
from doc_qa.parsing import ensure_q_heading, extract_final_agent_text, normalize_or_fail_closed
from doc_qa.prompts import NOT_FOUND


def test_partial_events_are_ignored():
    events = [
        make_event("strea", partial=True),
        make_event("streamed", partial=True),
        make_event("streamed"),
    ]
    assert extract_final_agent_text(events) == "streamed"


def test_events_without_content_are_skipped():
    assert extract_final_agent_text([make_event("only one")]) == "only one"


def test_empty_response_fails_closed():
    assert normalize_or_fail_closed("   ") == NOT_FOUND
    assert normalize_or_fail_closed("real") == "real"


def test_heading_added_when_missing():
    assert ensure_q_heading("body", 3, "Q?").startswith("## Q3: Q?")


def test_heading_not_duplicated():
    already = "## Q3: Q?\n\nbody"
    assert ensure_q_heading(already, 3, "Q?") == already


def test_wrong_heading_is_prefixed():
    # A level-2 heading for a different question must not be mistaken for this one's.
    assert ensure_q_heading("## Q9: other\n\nbody", 3, "Q?").startswith("## Q3: Q?")
