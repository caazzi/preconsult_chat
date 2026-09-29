"""
Clinical Agent Service (Replacing RAG).

This module replaces the old vector-search retrieval system with pure,
highly-optimized Clinical Prompt Engineering using established medical
frameworks (OPQRST and SAMPLE).

Output contract: the model is given a ``report_questions`` tool so it returns a
typed ``string[]`` rather than numbered prose the client has to regex-split.
``stream_interview_questions`` yields a typed event stream (``StreamEvent``):
live ``text`` deltas (kept for back-compat / progressive rendering) followed by
a terminal ``questions`` event with the structured list. Consumers that only
understand text can ignore the terminal event.
"""
import logging
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, Union
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from preconsult.core.llm import get_llm


# Structured-output tool the model must call to return the final questions.
REPORT_QUESTIONS_TOOL = {
    "name": "report_questions",
    "description": (
        "Report the final set of 3 to 5 clinical follow-up questions. "
        "Each question must be a single, clear, open-ended question. "
        "Call this exactly once as your final action; do not also emit prose."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 5,
                "description": "Ordered list of 3-5 single-point questions.",
            }
        },
        "required": ["questions"],
    },
}


@dataclass
class StreamEvent:
    """One typed unit of the question stream.

    ``kind="text"`` carries a raw model delta for live rendering.
    ``kind="questions"`` carries the final structured list (terminal event).
    """

    kind: Literal["text", "questions"]
    value: Union[str, list[str]]


def get_language_instructions(lang: str) -> dict:
    if lang == 'pt':
        return {
            "initial_q_instruction": "IDIOMA E TOM: Todas as perguntas DEVEM ser geradas em Português do Brasil claro, empático e acessível a leigos.",
            "follow_up_q_instruction": "Todas as perguntas devem ser em Português.",
            "summary_instruction": "Os *valores* do JSON devem ser em Português. As *chaves* devem permanecer em Inglês.",
            "example_question": 'Por exemplo, "Quando este sintoma começou?".',
            "not_mentioned": "Não mencionado"
        }
    return {
        "initial_q_instruction": "LANGUAGE & TONE: All questions MUST be generated in clear, empathetic, layperson-accessible English.",
        "follow_up_q_instruction": "All questions must be in English.",
        "summary_instruction": "The JSON *values* must be in English. The JSON *keys* must remain in English.",
        "example_question": 'For example, "When did this symptom start?".',
        "not_mentioned": "Not mentioned"
    }

# --- Sprint 1: Single Interview Chain ---
_interview_chain: Runnable | None = None

def get_interview_chain() -> Runnable:
    """Single interview chain. Receives full form context, generates up to 5 targeted questions."""
    global _interview_chain
    if _interview_chain is None:
        logging.info("Building interview chain...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "<role>\n"
                "You are a compassionate, highly precise clinical intake assistant helping a patient prepare for a medical appointment.\n"
                "Your objective is to generate up to 5 targeted, open-ended follow-up questions to capture what the form could not: "
                "the nuanced, specific details of the patient's current complaint that will maximize the doctor's efficiency.\n"
                "</role>\n\n"
                "<clinical_framework>\n"
                "Apply the core principles of OPQRST and SAMPLE clinical intake frameworks to explore missing details:\n"
                "- OPQRST: Onset (when/how it started), Provocative/Palliative (what makes it better or worse), "
                "Quality (nature of pain/symptom), Region/Radiation (location and if it spreads), Severity (1-10 scale or impact), Timing (frequency/duration).\n"
                "- SAMPLE: Associated Signs/Symptoms, Allergies, Medications, Past history, Last oral intake, Events leading up.\n"
                "Tailor the focus of your questions specifically to the requested specialty: {specialist}.\n"
                "</clinical_framework>\n\n"
                "<safety_guardrails>\n"
                "1. YOU ARE NOT A DOCTOR. Never suggest diagnoses, treatments, medications, or potential causes for symptoms.\n"
                "2. NO DUPLICATION: Do not ask about information already collected in the form (do not re-ask about medications, "
                "known conditions, or allergies already listed).\n"
                "3. EMERGENCY RED FLAGS PROTOCOL: If the chief complaint or symptoms indicate a critical emergency "
                "(e.g., severe chest pain, sudden difficulty breathing, loss of consciousness, acute stroke symptoms, severe trauma), "
                "output ONLY an emergency warning advising immediate emergency care. Begin that warning with the exact token "
                "[EMERGENCY ALERT] and instruct the patient to call emergency services immediately. Do not generate questions.\n"
                "4. LAYPERSON ACCESSIBILITY: Use simple, empathetic language accessible to non-medical lay people (6th-grade reading level). Avoid clinical jargon (e.g., instead of 'radiation', ask if pain travels elsewhere).\n"
                "5. SINGLE-POINT QUESTIONS: Generate between 3 and 5 numbered questions. Each item must contain only ONE clear question.\n"
                "</safety_guardrails>\n\n"
                "<output_format>\n"
                "- If emergency: Output ONLY the emergency warning message, beginning with [EMERGENCY ALERT]. Do not generate questions.\n"
                "- Otherwise: Output ONLY a numbered list of 3 to 5 questions, one per line, in the exact form '1. <question>'. "
                "No preamble, no headings, no pleasantries, no markdown emphasis.\n"
                "</output_format>\n\n"
                "<language_setting>\n"
                "{language_instruction}\n"
                "</language_setting>"
            )),
            ("human", (
                "Age bracket: {age_bracket}\n"
                "Biological sex: {sex}\n"
                "Specialist: {specialist}\n"
                "Chief complaint: {chief_complaint}\n"
                "Duration: {duration}\n"
                "Additional detail: {complaint_detail}\n"
                "Pre-existing conditions: {conditions}\n"
                "Current medications: {medications}\n"
                "Drug allergies: {allergies}\n"
                "Family history: {family_history}\n"
                "Smoking: {smoking}\n"
                "Alcohol: {alcohol}"
            )),
        ])
        _interview_chain = prompt | get_llm().bind_tools([REPORT_QUESTIONS_TOOL])
    return _interview_chain


def _to_dict(msg) -> dict:
    """Normalize a message into a plain dict for the streaming consumer.

    Kept dependency-free so tests can feed either a real BaseMessage or a fake
    exposing ``content`` / ``tool_calls``.
    """
    if isinstance(msg, dict):
        return msg
    content = getattr(msg, "content", "")
    tool_calls = getattr(msg, "tool_calls", None) or []
    return {"content": content, "tool_calls": tool_calls}


def _extract_questions(tool_call) -> list[str] | None:
    """Pull a ``questions`` list out of a ``report_questions`` tool call."""
    if not isinstance(tool_call, dict):
        return None
    if tool_call.get("name") != REPORT_QUESTIONS_TOOL["name"]:
        return None
    args = tool_call.get("args") or {}
    questions = args.get("questions")
    if isinstance(questions, list):
        cleaned = [q.strip() for q in questions if isinstance(q, str) and q.strip()]
        return cleaned or None
    return None


async def stream_interview_questions(
    session_data: dict,
    lang: str,
    chain: Runnable
) -> AsyncGenerator[StreamEvent, None]:
    """Streams typed events: text deltas, then a terminal structured list.

    Yields ``StreamEvent(kind="text")`` for each model content delta (for live
    rendering / back-compat) and, when the model calls ``report_questions``, a
    final ``StreamEvent(kind="questions")`` carrying the structured list.
    """
    logging.info(f"Streaming interview questions (lang={lang}).")
    lang_instructions = get_language_instructions(lang)

    def join_list(items):
        return ", ".join(items) if items else "None"

    input_dict = {
        "age_bracket": session_data.get("age_bracket", ""),
        "sex": session_data.get("sex", ""),
        "specialist": session_data.get("specialist", ""),
        "chief_complaint": session_data.get("chief_complaint", ""),
        "duration": session_data.get("duration", ""),
        "complaint_detail": session_data.get("complaint_detail", "") or "None",
        "conditions": join_list(session_data.get("conditions", [])),
        "medications": join_list(session_data.get("medications", [])),
        "allergies": session_data.get("allergies", "") or "None",
        "family_history": join_list(session_data.get("family_history", [])),
        "smoking": session_data.get("smoking", ""),
        "alcohol": session_data.get("alcohol", ""),
        "language_instruction": lang_instructions["initial_q_instruction"],
    }

    final_questions: list[str] | None = None
    async for msg in chain.astream(input_dict):
        data = _to_dict(msg)
        content = data.get("content")
        if isinstance(content, str) and content:
            yield StreamEvent(kind="text", value=content)
        for tool_call in data.get("tool_calls", []) or []:
            questions = _extract_questions(tool_call)
            if questions:
                final_questions = questions

    if final_questions is not None:
        yield StreamEvent(kind="questions", value=final_questions)


