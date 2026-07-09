"""LLM API tests — mocked for CI, one integration test gated for real credentials."""
import os
import pytest
from unittest.mock import patch
from langchain_core.language_models import FakeListChatModel

_REAL_PROJECT = "securemed-chat-494521"

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_singletons():
    import preconsult.services.agent_service as agent_service
    agent_service._interview_chain = None


# ── Mocked tests (run in every CI) ────────────────────────────


@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_llm_generates_questions_in_english_mocked(mock_get_llm):
    from preconsult.services.agent_service import get_interview_chain, stream_interview_questions
    fake_llm = FakeListChatModel(responses=["1. When did the pain start?\n2. Does it radiate?"])
    mock_get_llm.return_value = fake_llm

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
    async for chunk in stream_interview_questions(session_data, "en", chain):
        questions.append(chunk)
    full_text = "".join(questions)
    assert len(full_text) > 20
    assert "?" in full_text


@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_llm_generates_questions_in_portuguese_mocked(mock_get_llm):
    from preconsult.services.agent_service import get_interview_chain, stream_interview_questions
    fake_llm = FakeListChatModel(responses=["1. Quando a dor começou?\n2. Ela irradia?"])
    mock_get_llm.return_value = fake_llm

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
    async for chunk in stream_interview_questions(session_data, "pt", chain):
        questions.append(chunk)
    full_text = "".join(questions)
    assert len(full_text) > 20
    assert "?" in full_text


@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_llm_detects_emergency_mocked(mock_get_llm):
    from preconsult.services.agent_service import get_interview_chain, stream_interview_questions
    fake_llm = FakeListChatModel(responses=["⚠️ EMERGENCY: Please call 911 immediately."])
    mock_get_llm.return_value = fake_llm

    chain = get_interview_chain()
    session_data = {
        "chief_complaint": "severe chest pain radiating to left arm, shortness of breath",
    }
    output = []
    async for chunk in stream_interview_questions(session_data, "en", chain):
        output.append(chunk)
    full_text = "".join(output).lower()
    keywords = ["emergency", "911", "immediate", "call"]
    assert any(k in full_text for k in keywords)


# ── Integration test (only runs with real GCP credentials & correct project) ──

@pytest.mark.skipif(
    os.environ.get("RUN_VERTEX_INTEGRATION") != "true",
    reason="Integration test: set RUN_VERTEX_INTEGRATION=true",
)
async def test_llm_real_vertex_call():
    os.environ["GOOGLE_CLOUD_PROJECT"] = _REAL_PROJECT
    from preconsult.services.agent_service import get_interview_chain

    chain = get_interview_chain()
    session_data = {
        "age_bracket": "26-35",
        "sex": "Female",
        "specialist": "Cardiology",
        "chief_complaint": "Chest pain when exercising",
        "duration": "2 weeks",
        "complaint_detail": "Sharp pain, goes away with rest",
        "conditions": "None",
        "medications": "None",
        "allergies": "None",
        "family_history": "None",
        "smoking": "Never",
        "alcohol": "Rarely",
        "language_instruction": "All questions must be in English.",
    }
    questions = []
    async for chunk in chain.astream(session_data):
        questions.append(chunk)
    full_text = "".join(questions)
    assert len(full_text) > 20
    assert "?" in full_text
