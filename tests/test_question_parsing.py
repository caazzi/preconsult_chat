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
