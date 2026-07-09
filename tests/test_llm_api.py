import os


_REAL_PROJECT = "securemed-chat-494521"
_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")

os.environ["GOOGLE_CLOUD_PROJECT"] = _REAL_PROJECT


import pytest


pytestmark = [
    pytest.mark.skipif(
        not _CREDENTIALS or not os.path.exists(_CREDENTIALS),
        reason="GOOGLE_APPLICATION_CREDENTIALS not set or file not found"
    ),
    pytest.mark.asyncio,
]


@pytest.fixture(autouse=True)
def _reset_singletons():
    import preconsult.services.agent_service as agent_service
    import preconsult.core.llm as llm_module
    agent_service._interview_chain = None
    llm_module._llm = None


async def test_llm_generates_questions_in_english():
    from preconsult.services.agent_service import get_interview_chain

    def join_list(items):
        return ", ".join(items) if items else "None"

    session_data = {
        "age_bracket": "26-35",
        "sex": "Female",
        "specialist": "Cardiology",
        "chief_complaint": "Chest pain when exercising",
        "duration": "2 weeks",
        "complaint_detail": "Sharp pain, goes away with rest",
        "conditions": join_list([]),
        "medications": join_list([]),
        "allergies": "None",
        "family_history": join_list([]),
        "smoking": "Never",
        "alcohol": "Rarely",
        "language_instruction": "All questions must be in English.",
    }
    chain = get_interview_chain()
    questions = []
    async for chunk in chain.astream(session_data):
        questions.append(chunk)
    full_text = "".join(questions)
    assert len(full_text) > 20
    assert "?" in full_text
    assert any(c.isdigit() for c in full_text)


async def test_llm_generates_questions_in_portuguese():
    from preconsult.services.agent_service import get_interview_chain

    def join_list(items):
        return ", ".join(items) if items else "None"

    session_data = {
        "age_bracket": "26-35",
        "sex": "Female",
        "specialist": "Cardiology",
        "chief_complaint": "Chest pain when exercising",
        "duration": "2 weeks",
        "complaint_detail": "Sharp pain, goes away with rest",
        "conditions": join_list([]),
        "medications": join_list([]),
        "allergies": "None",
        "family_history": join_list([]),
        "smoking": "Never",
        "alcohol": "Rarely",
        "language_instruction": "Todas as perguntas devem ser em Português.",
    }
    chain = get_interview_chain()
    questions = []
    async for chunk in chain.astream(session_data):
        questions.append(chunk)
    full_text = "".join(questions)
    assert len(full_text) > 20
    assert any(c.isdigit() for c in full_text)


async def test_llm_detects_emergency():
    from preconsult.services.agent_service import get_interview_chain

    session_data = {
        "age_bracket": "",
        "sex": "",
        "specialist": "",
        "chief_complaint": "severe chest pain radiating to left arm, shortness of breath",
        "duration": "",
        "complaint_detail": "None",
        "conditions": "None",
        "medications": "None",
        "allergies": "None",
        "family_history": "None",
        "smoking": "",
        "alcohol": "",
        "language_instruction": "All questions must be in English.",
    }
    chain = get_interview_chain()
    questions = []
    async for chunk in chain.astream(session_data):
        questions.append(chunk)
    full_text = "".join(questions).lower()
    keywords = ["emergency", "911", "immediate", "call", "seek",
                "chest pain", "shortness of breath", "left arm", "nausea",
                "dizziness", "sweating"]
    assert any(k in full_text for k in keywords), (
        f"No relevant clinical keywords found in: {full_text}"
    )
