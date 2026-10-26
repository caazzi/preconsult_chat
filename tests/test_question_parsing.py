from preconsult.core.parsing import split_questions, is_emergency_trigger

# NOTE: the canonical behavior matrix for split_questions / is_emergency_trigger
# lives in contracts/parsing_vectors.json and is exercised by tests/test_contracts.py
# (so both Python and the future TS port are pinned to one source). This module
# keeps only the cases that are NOT representable as simple input->output vectors
# (stream reassembly, conflation with unrelated content).


def test_split_questions_reassembly_across_chunks():
    """SSE pushes substrings; re-parsing each accumulated buffer must converge.

    Model the consumption loop in state.py.get_interview_questions: a buffer
    grows chunk-by-chunk and split_questions(buffer) runs after every chunk.
    A well-formed numbered stream must yield the same final set whether parsed
    in one shot or after accumulating arbitrary mid-word boundaries.
    """
    final_text = "\n1. One?\n2. Two?\n3. Three?"
    completed = split_questions(final_text)

    # Simulate realistic SSE token boundaries that cut lines mid-question.
    chunks = ["\n1. ", "One?\n2", ". Two?\n3", ". Three?"]
    buffer = ""
    for chunk in chunks:
        buffer += chunk
        current = split_questions(buffer)
        # Partial buffers may under-report but must never crash.
        assert isinstance(current, list)
        assert all(isinstance(q, str) for q in current)

    assembled = split_questions(buffer)
    assert assembled == completed == ["One?", "Two?", "Three?"]


def test_split_questions_numbered_then_newline_fallback_returns_full_lines():
    """When a buffer has only one numbered fragment, fall back to newline split."""
    buffer = "Only one numbered fragment? \nsecond line"
    qs = split_questions(buffer)
    assert len(qs) == 2


def test_is_emergency_trigger_only_matches_tokens_not_numbers():
    """911/emergency must not be triggered by unrelated substrings.

    The vector matrix covers the common positives; this pins the negative that
    a bare number like 1234 must not collide with the 911 token.
    """
    assert is_emergency_trigger("session id 1234") is False
    assert is_emergency_trigger("the patient is fine") is False
