import re


def _split_questions(buffer: str) -> list[str]:
    qs = [q.strip() for q in re.split(r'\n(?:\d+[\.\)]|\-)\s*', '\n' + buffer) if q.strip()]
    if len(qs) <= 1:
        qs = [q.strip() for q in buffer.strip().split('\n') if q.strip()]
    return qs


def test_parse_questions_numbered():
    buffer = "\n1. Question one?\n2. Question two?\n3. Question three?"
    qs = _split_questions(buffer)
    assert len(qs) == 3
    assert qs[0] == "Question one?"
    assert qs[1] == "Question two?"
    assert qs[2] == "Question three?"


def test_parse_questions_parentheses():
    buffer = "1) Question one?\n2) Question two?"
    qs = _split_questions(buffer)
    assert len(qs) == 2
    assert qs[0] == "Question one?"


def test_parse_questions_dash():
    buffer = "- Question one?\n- Question two?"
    qs = _split_questions(buffer)
    assert len(qs) == 2


def test_parse_questions_fallback_newline():
    buffer = "Question one?\nQuestion two?\nQuestion three?"
    qs = _split_questions(buffer)
    assert len(qs) == 3
    assert qs[1] == "Question two?"


def test_parse_questions_single_line():
    buffer = "Just one long question?"
    qs = _split_questions(buffer)
    assert len(qs) == 1


def test_parse_questions_empty():
    assert _split_questions("") == []
    assert _split_questions("   ") == []
