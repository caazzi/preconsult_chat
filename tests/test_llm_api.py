"""LLM API tests — mocked for CI, one integration test gated for real credentials."""
import os
import pytest
from unittest.mock import patch
from tests.fakes import ToolCallingFakeLLM

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _reset_singletons():
    import preconsult.services.agent_service as agent_service
    agent_service._interview_chain = None


# ── Provider wiring (Vertex default, Bedrock opt-in) ──────────


async def test_get_llm_builds_vertex_client_by_default():
    """The deployed provider is Vertex: get_llm must build ChatVertexAI and cache it."""
    import preconsult.core.llm as llm_module

    original = llm_module._llm
    llm_module._llm = None
    try:
        with patch("langchain_google_vertexai.ChatVertexAI") as mock_chat:
            instance = mock_chat.return_value
            first = llm_module.get_llm()
            assert first is instance
            mock_chat.assert_called_once()
            kwargs = mock_chat.call_args.kwargs
            assert kwargs["model_name"] == llm_module.LLM_MODEL
            assert kwargs["project"] == llm_module.PROJECT_ID
            assert kwargs["location"] == llm_module.VERTEX_REGION
            assert kwargs["streaming"] is True
            # Second call returns the cached singleton without rebuilding.
            assert llm_module.get_llm() is instance
            assert mock_chat.call_count == 1
    finally:
        llm_module._llm = original


async def test_get_llm_builds_bedrock_client_when_selected(monkeypatch):
    import preconsult.core.llm as llm_module

    original = llm_module._llm
    llm_module._llm = None
    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "bedrock")
    try:
        with patch("langchain_aws.ChatBedrockConverse") as mock_chat:
            instance = mock_chat.return_value
            assert llm_module.get_llm() is instance
            kwargs = mock_chat.call_args.kwargs
            assert kwargs["model"] == llm_module.LLM_MODEL
            assert kwargs["region_name"] == llm_module.BEDROCK_REGION
            assert llm_module.get_llm() is instance
            assert mock_chat.call_count == 1
    finally:
        llm_module._llm = original


async def test_bedrock_without_the_extra_fails_with_an_actionable_message(
    monkeypatch,
):
    """The default image does not install boto3/botocore; say so, don't 500."""
    import sys

    import preconsult.core.llm as llm_module

    original = llm_module._llm
    llm_module._llm = None
    monkeypatch.setattr(llm_module, "LLM_PROVIDER", "bedrock")
    monkeypatch.setitem(sys.modules, "langchain_aws", None)
    try:
        with pytest.raises(RuntimeError, match="extra bedrock"):
            llm_module.get_llm()
    finally:
        llm_module._llm = original


async def test_only_the_selected_provider_client_is_constructed(monkeypatch):
    """Lazy imports: picking one provider must not touch the other package."""
    import preconsult.core.llm as llm_module

    original = llm_module._llm
    llm_module._llm = None
    try:
        with patch("langchain_google_vertexai.ChatVertexAI") as vertex_chat, patch(
            "langchain_aws.ChatBedrockConverse"
        ) as bedrock_chat:
            llm_module.get_llm()
            vertex_chat.assert_called_once()
            bedrock_chat.assert_not_called()
    finally:
        llm_module._llm = original


# ── Mocked tests (run in every CI) ────────────────────────────


@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_llm_generates_questions_in_english_mocked(mock_get_llm):
    from preconsult.services.agent_service import get_interview_chain, stream_interview_questions
    fake_llm = ToolCallingFakeLLM(text="1. When did the pain start?\n2. Does it radiate?", questions=["When did the pain start?", "Does it radiate?"])
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
    events = []
    async for event in stream_interview_questions(session_data, "en", chain):
        events.append(event)
    full_text = "".join(e.value for e in events if e.kind == "text")
    assert len(full_text) > 20
    assert "?" in full_text


@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_llm_generates_questions_in_portuguese_mocked(mock_get_llm):
    from preconsult.services.agent_service import get_interview_chain, stream_interview_questions
    fake_llm = ToolCallingFakeLLM(text="1. Quando a dor começou?\n2. Ela irradia?", questions=["Quando a dor começou?", "Ela irradia?"])
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
    events = []
    async for event in stream_interview_questions(session_data, "pt", chain):
        events.append(event)
    full_text = "".join(e.value for e in events if e.kind == "text")
    assert len(full_text) > 20
    assert "?" in full_text


@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_llm_detects_emergency_mocked(mock_get_llm):
    from preconsult.services.agent_service import get_interview_chain, stream_interview_questions
    fake_llm = ToolCallingFakeLLM(text="⚠️ EMERGENCY: Please call 911 immediately.")
    mock_get_llm.return_value = fake_llm

    chain = get_interview_chain()
    session_data = {
        "chief_complaint": "severe chest pain radiating to left arm, shortness of breath",
    }
    output = []
    async for event in stream_interview_questions(session_data, "en", chain):
        if event.kind == "text":
            output.append(event.value)
    full_text = "".join(output).lower()
    keywords = ["emergency", "911", "immediate", "call"]
    assert any(k in full_text for k in keywords)


# ── Integration test: runs in CI when AWS/Bedrock credentials are present ──


def _can_run_integration():
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    return bool(
        os.environ.get("AWS_ACCESS_KEY_ID")
        or os.environ.get("AWS_PROFILE")
        or (cred_path and os.path.isfile(cred_path))
    )


@pytest.mark.skipif(
    not _can_run_integration(),
    reason="Integration test: requires AWS Bedrock credentials "
    "(AWS_ACCESS_KEY_ID / AWS_PROFILE / ambient role).",
)
async def test_llm_real_bedrock_call():
    from preconsult.services.agent_service import get_interview_chain, stream_interview_questions

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
    events = []
    async for event in stream_interview_questions(session_data, "en", chain):
        events.append(event)
    full_text = "".join(e.value for e in events if e.kind == "text")
    structured = [e.value for e in events if e.kind == "questions"]
    # The live model should either stream text or emit a structured list.
    assert full_text or structured
    if structured:
        assert 3 <= len(structured[0]) <= 5
