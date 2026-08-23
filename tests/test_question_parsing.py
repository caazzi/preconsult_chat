from preconsult.core.parsing import split_questions, is_emergency_trigger


def test_parse_questions_numbered():
    buffer = "\n1. Question one?\n2. Question two?\n3. Question three?"
    qs = split_questions(buffer)
    assert len(qs) == 3
    assert qs[0] == "Question one?"
    assert qs[1] == "Question two?"
    assert qs[2] == "Question three?"


def test_parse_questions_parentheses():
    buffer = "1) Question one?\n2) Question two?"
    qs = split_questions(buffer)
    assert len(qs) == 2
    assert qs[0] == "Question one?"


def test_parse_questions_dash():
    buffer = "- Question one?\n- Question two?"
    qs = split_questions(buffer)
    assert len(qs) == 2


def test_parse_questions_fallback_newline():
    buffer = "Question one?\nQuestion two?\nQuestion three?"
    qs = split_questions(buffer)
    assert len(qs) == 3
    assert qs[1] == "Question two?"


def test_parse_questions_single_line():
    buffer = "Just one long question?"
    qs = split_questions(buffer)
    assert len(qs) == 1


def test_parse_questions_empty():
    assert split_questions("") == []
    assert split_questions("   ") == []


def test_is_emergency_trigger_english():
    assert is_emergency_trigger("EMERGENCY: call 911") is True
    assert is_emergency_trigger("please dial 911 now") is True


def test_is_emergency_trigger_portuguese():
    assert is_emergency_trigger("[ALERTA DE EMERGÊNCIA] ligue 192") is True
    assert is_emergency_trigger("urgencia nao mencionada") is True


def test_is_emergency_trigger_non_emergency():
    assert is_emergency_trigger("1. Question one?\n2. Question two?") is False
    assert is_emergency_trigger("") is False


# --- Port-matrix edge cases (see docs/parsing-port-spec.md) ---


def test_split_questions_handles_multiple_trailing_newlines():
    buffer = "\n1. One?\n2. Two?\n\n\n"
    qs = split_questions(buffer)
    assert qs == ["One?", "Two?"]


def test_split_questions_handles_crlf():
    buffer = "1. One?\r\n2. Two?\r\n3. Three?"
    qs = split_questions(buffer)
    assert qs == ["One?", "Two?", "Three?"]


def test_split_questions_mixed_separators_in_one_buffer():
    buffer = "\n1. One?\n- Two?\n3) Three?"
    qs = split_questions(buffer)
    assert qs == ["One?", "Two?", "Three?"]


def test_split_questions_strips_leading_spaces_after_number():
    buffer = "\n1.   One?\n2.    Two?"
    qs = split_questions(buffer)
    assert qs == ["One?", "Two?"]


def test_split_questions_multiline_question_kept_intact():
    buffer = "\n1. Is this one long\nquestion spanning two lines?\n2. Second?"
    qs = split_questions(buffer)
    assert qs == ["Is this one long\nquestion spanning two lines?", "Second?"]


def test_split_questions_reassembly_across_chunks():
    """SSE pushes substrings; re-parsing each accumulated buffer must converge.

    Model the consumption loop in state.py.get_interview_questions: a buffer
    grows chunk-by-chunk and split_questions(buffer) runs after every chunk.
    A well-formed numbered stream must yield the same final set whether parsed
    in one shot or after accumulating arbitrary mid-word boundaries.
    """
    from preconsult.core.parsing import split_questions

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


def test_is_emergency_trigger_case_insensitive_accent_insensitive():
    assert is_emergency_trigger("EMERGÊNCIA: ligue 192") is True
    assert is_emergency_trigger("Urgência") is True
    assert is_emergency_trigger("URGENCIA") is True
    assert is_emergency_trigger("call 911 immediately") is True


def test_is_emergency_trigger_only_matches_whole_tokens():
    """911/emergency must not be triggered by unrelated substrings."""
    assert is_emergency_trigger("emergency room visit") is True  # token present
    assert is_emergency_trigger("please ring my doctor today") is False
    assert is_emergency_trigger("session id 1234") is False
    assert is_emergency_trigger("the patient is fine") is False
