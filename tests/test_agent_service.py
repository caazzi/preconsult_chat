import pytest
from unittest.mock import patch
from preconsult.services.agent_service import (
    get_language_instructions,
    get_interview_chain,
    stream_interview_questions,
    StreamEvent,
)
import preconsult.services.agent_service as agent_service
from tests.fakes import ToolCallingFakeLLM, session_payload

@pytest.fixture(autouse=True)
def reset_singletons():
    agent_service._interview_chain = None

def test_language_instructions_en():
    instr = get_language_instructions("en")
    assert "English" in instr["initial_q_instruction"]
    assert "not mentioned" in instr["not_mentioned"].lower()

def test_language_instructions_pt():
    instr = get_language_instructions("pt")
    assert "Português" in instr["initial_q_instruction"]
    assert "não mencionado" in instr["not_mentioned"].lower()

@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_interview_chain_streams_questions(mock_get_llm):
    fake_llm = ToolCallingFakeLLM(
        text="1. Question A?\n2. Question B?",
        questions=["Question A?", "Question B?"],
    )
    mock_get_llm.return_value = fake_llm
    
    chain = get_interview_chain()
    session_data = session_payload(
        duration="Weeks", smoking="Never", alcohol="Rarely"
    )
    
    events = []
    async for event in stream_interview_questions(session_data, "en", chain):
        events.append(event)
    
    full_text = "".join(e.value for e in events if e.kind == "text")
    structured = [e.value for e in events if e.kind == "questions"]
    assert "Question A" in full_text
    assert structured == [["Question A?", "Question B?"]]
    assert mock_get_llm.called

@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_interview_chain_pt(mock_get_llm):
    fake_llm = ToolCallingFakeLLM(text="1. Pergunta A?", questions=["Pergunta A?"])
    mock_get_llm.return_value = fake_llm
    
    chain = get_interview_chain()
    session_data = {
        "age_bracket": "26-35",
        "sex": "Female",
        "specialist": "Cardiology",
    }
    
    events = []
    async for event in stream_interview_questions(session_data, "pt", chain):
        events.append(event)
    
    full_text = "".join(e.value for e in events if e.kind == "text")
    assert "Pergunta A" in full_text
    assert mock_get_llm.called

def test_interview_chain_prompt_contains_all_form_fields():
    chain = get_interview_chain()
    prompt = chain.steps[0]
    expected_vars = [
        "age_bracket", "sex", "specialist", "chief_complaint", "duration",
        "complaint_detail", "conditions", "medications", "allergies",
        "family_history", "smoking", "alcohol", "language_instruction"
    ]
    for var in expected_vars:
        assert var in prompt.input_variables

def test_interview_chain_binds_report_questions_tool():
    """The chain must bind the structured report_questions tool."""
    get_interview_chain()
    assert agent_service.REPORT_QUESTIONS_TOOL["name"] == "report_questions"


def test_extract_questions_from_tool_call():
    from preconsult.services.agent_service import _extract_questions

    assert _extract_questions(
        {"name": "report_questions", "args": {"questions": ["A?", " B? ", ""]}}
    ) == ["A?", "B?"]
    # wrong tool / non-dict / malformed args -> None
    assert _extract_questions({"name": "other", "args": {"questions": ["A?"]}}) is None
    assert _extract_questions("not-a-call") is None
    assert _extract_questions({"name": "report_questions", "args": {}}) is None
    assert _extract_questions({"name": "report_questions", "args": {"questions": []}}) is None


def test_to_dict_normalizes_message_and_dict():
    from langchain_core.messages import AIMessageChunk
    from preconsult.services.agent_service import _to_dict

    assert _to_dict({"content": "x"}) == {"content": "x", "tool_calls": []}
    out = _to_dict(AIMessageChunk(content="hello"))
    assert out["content"] == "hello"
    assert out["tool_calls"] == []


def test_to_dict_flattens_content_blocks():
    """langchain-core 1.x allows content to be a list of blocks.

    A str-only consumer would drop every delta from such a message, so the
    normaliser flattens text blocks and ignores non-text ones.
    """
    from langchain_core.messages import AIMessageChunk
    from preconsult.services.agent_service import _to_dict

    out = _to_dict(
        AIMessageChunk(
            content=[
                {"type": "text", "text": "When did it "},
                {"type": "text", "text": "start?"},
                {"type": "image_url", "image_url": {"url": "ignored"}},
            ]
        )
    )
    assert out["content"] == "When did it start?"
    assert _to_dict({"content": ["a", "b"]})["content"] == "ab"
    assert _to_dict({"content": None})["content"] == ""

def test_interview_prompt_contains_emergency_rule():
    chain = get_interview_chain()
    prompt = chain.steps[0]
    system_msg = str(prompt.messages[0])
    assert "emergency" in system_msg.lower()
    assert "do not generate questions" in system_msg.lower()

def test_interview_prompt_contains_xml_and_frameworks():
    chain = get_interview_chain()
    prompt = chain.steps[0]
    system_msg = str(prompt.messages[0])
    assert "<role>" in system_msg
    assert "<clinical_framework>" in system_msg
    assert "<safety_guardrails>" in system_msg
    assert "OPQRST" in system_msg
    assert "SAMPLE" in system_msg

@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_emergency_text_is_still_streamed_as_text(mock_get_llm):
    """An emergency phrasing arrives as text (no tool call) and must surface
    verbatim so the client's output-side is_emergency_trigger backstop fires."""
    fake_llm = ToolCallingFakeLLM(text="⚠️ EMERGENCY: Please call 911 immediately.")
    mock_get_llm.return_value = fake_llm
    
    chain = get_interview_chain()
    session_data = {
        "chief_complaint": "severe chest pain"
    }
    
    output = []
    async for event in stream_interview_questions(session_data, "en", chain):
        assert isinstance(event, StreamEvent)
        if event.kind == "text":
            output.append(event.value)
        
    full_text = "".join(output)
    
    lower_text = full_text.lower()
    assert any(word in lower_text for word in ["emergency", "911", "immediate"])
    assert not full_text.startswith("1.")



