import pytest
from unittest.mock import patch
from langchain_core.language_models import FakeListChatModel
from preconsult.services.agent_service import (
    get_language_instructions,
    get_interview_chain,
    stream_interview_questions
)
import preconsult.services.agent_service as agent_service

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
    fake_llm = FakeListChatModel(responses=["1. Question A?\n2. Question B?"])
    mock_get_llm.return_value = fake_llm
    
    chain = get_interview_chain()
    session_data = {
        "age_bracket": "26-35",
        "sex": "Female",
        "specialist": "Cardiology",
        "chief_complaint": "Chest pain",
        "duration": "Weeks",
        "complaint_detail": "",
        "conditions": [],
        "medications": [],
        "allergies": "",
        "family_history": [],
        "smoking": "Never",
        "alcohol": "Rarely"
    }
    
    questions = []
    async for chunk in stream_interview_questions(session_data, "en", chain):
        questions.append(chunk)
    
    full_text = "".join(questions)
    assert "Question A" in full_text
    assert mock_get_llm.called

@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_interview_chain_pt(mock_get_llm):
    fake_llm = FakeListChatModel(responses=["1. Pergunta A?"])
    mock_get_llm.return_value = fake_llm
    
    chain = get_interview_chain()
    session_data = {
        "age_bracket": "26-35",
        "sex": "Female",
        "specialist": "Cardiology",
    }
    
    questions = []
    async for chunk in stream_interview_questions(session_data, "pt", chain):
        questions.append(chunk)
    
    full_text = "".join(questions)
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

def test_interview_prompt_contains_emergency_rule():
    chain = get_interview_chain()
    prompt = chain.steps[0]
    system_msg = str(prompt.messages[0])
    assert "emergency" in system_msg.lower()
    assert "do not generate questions" in system_msg.lower()

@pytest.mark.asyncio
@patch("preconsult.services.agent_service.get_llm")
async def test_emergency_detection_in_output(mock_get_llm):
    fake_llm = FakeListChatModel(responses=["⚠️ EMERGENCY: Please call 911 immediately."])
    mock_get_llm.return_value = fake_llm
    
    chain = get_interview_chain()
    session_data = {
        "chief_complaint": "severe chest pain"
    }
    
    output = []
    async for chunk in stream_interview_questions(session_data, "en", chain):
        output.append(chunk)
        
    full_text = "".join(output)
    
    lower_text = full_text.lower()
    assert any(word in lower_text for word in ["emergency", "911", "immediate"])
    assert not full_text.startswith("1.")


