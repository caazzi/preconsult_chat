# Implementation Plan: SecureMed Chat Phase 3

**For agents:** Each sprint is self-contained. Read the sprint you are assigned, read the files listed under "Read first", then implement. Reference `docs/PRD.md` for full product context.

**Approach:** TDD — write tests first, implement to make them pass, delete old tests atomically with the code they cover. Never skip the security test suite (`tests/test_security.py`) — run it as a gate at the end of every sprint.

---

## Project structure reference

```
preconsult_chat/
├── src/preconsult/
│   ├── api/endpoints.py          # FastAPI routes
│   ├── core/config.py            # Env config
│   ├── core/llm.py               # Vertex AI LLM singleton
│   ├── services/agent_service.py # LLM chains (prompt engineering)
│   ├── services/pdf_service.py   # In-memory PDF generation
│   ├── services/session_service.py # Redis session CRUD
│   └── main.py                   # FastAPI app
├── reflex_app/securemed/
│   ├── securemed.py              # Reflex UI components
│   ├── state.py                  # Reflex state + event handlers
│   └── i18n.py                   # EN/PT translation strings
└── tests/
    ├── conftest.py               # Sets env vars for CI (no real Redis/GCP needed)
    ├── test_agent_service.py
    ├── test_api_integration.py
    ├── test_pdf_service.py
    ├── test_security.py          # Static/structural regression tests — never delete these
    └── test_session_service.py   # Redis session logic — not modified in any sprint
```

---

## Architecture being implemented

**Current (to be replaced):**
1. `POST /api/session/init` (age, gender, lang) → session_id
2. `POST /api/initial-questions-stream` (session_id, chief_complaint) → OPQRST questions (LLM call 1)
3. `POST /api/follow-up-questions-stream` (session_id, initial_answers) → SAMPLE questions (LLM call 2)
4. `POST /api/summarize-and-generate-pdf` (session_id, follow_up_answers) → LLM summarizes → PDF

**Target (what you are building):**
1. Frontend collects full structured form (Steps 1–4: demographics, chief complaint, medical history, lifestyle)
2. `POST /api/session/init` (ALL form fields) → session_id
3. `POST /api/interview-questions-stream` (session_id) → ONE LLM call using full form context → up to 5 targeted questions
4. Patient answers the questions
5. `POST /api/generate-pdf` (session_id, qa_pairs) → deterministic PDF, NO LLM call

**Privacy principle:** The patient's free-text answers (the most sensitive content) never go back to the LLM. Only the structured form data does.

---

## Sprint dependency chain

```
Sprint 1 (new API contract)
    ├── Sprint 2 (PDF service rewrite) ← no dependency on Sprint 3, can run in parallel
    └── Sprint 3 (agent chain rewrite) ← no dependency on Sprint 2, can run in parallel
            └── Sprint 4 (frontend)
                    └── Sprint 5 (fixes)
                            └── Sprint 6 (UX polish)
```

---

## Sprint 1 — New API Contract & Session Schema

**Goal:** Define the new endpoints and full session data model. Old endpoints stay alive for backward compatibility until Sprint 3.

### Read first
- `src/preconsult/api/endpoints.py` (full file)
- `src/preconsult/services/agent_service.py` (full file)
- `tests/test_api_integration.py` (full file)

### New session schema
All fields below are stored in Redis via `session_service.create_session()`. The existing `session_service.py` accepts any dict — no changes needed there.

```python
{
    # Step 1 — Demographics
    "age_bracket": str,       # "18-25" | "26-35" | "36-45" | "46-60" | "60+"
    "sex": str,               # "Male" | "Female" | "Intersex"
    "lang": str,              # "en" | "pt"
    # Step 2 — Chief Complaint
    "specialist": str,        # free text, e.g. "Gastroenterologist"
    "chief_complaint": str,   # free text, max 500 chars
    "duration": str,          # "Started today" | "A few days" | "Weeks" | "Months" | "Years"
    "complaint_detail": str,  # free text, optional
    # Step 3 — Medical History
    "conditions": list[str],  # e.g. ["Hypertension", "Diabetes"]
    "medications": list[str], # e.g. ["Losartan 50mg", "Vitamin D"]
    "allergies": str,         # free text or "None"
    # Step 4 — Lifestyle & Family
    "family_history": list[str],  # e.g. ["Cancer", "Diabetes"]
    "smoking": str,           # "Currently smoke" | "Former smoker" | "Never smoked"
    "alcohol": str,           # "Rarely" | "Socially" | "Frequently" | "Never"
}
```

### Changes to `endpoints.py`

1. **Update `SessionInitRequest`** to accept the full schema above (all fields required except `conditions`, `medications`, `family_history` which default to empty list, and `complaint_detail`/`allergies` which default to empty string).

2. **Add new Pydantic model `QAPair`:**
```python
class QAPair(BaseModel):
    question: str
    answer: str = Field(..., max_length=2000)
```

3. **Add new Pydantic model `GeneratePdfRequest`:**
```python
class GeneratePdfRequest(BaseModel):
    session_id: str
    qa_pairs: list[QAPair] = Field(..., min_length=1, max_length=5)
```

4. **Add new endpoint `POST /api/interview-questions-stream`:**
- Accepts `InitialRequest` (session_id + chief_complaint field can be removed — chief_complaint is now in the session)
- Actually: accepts just `{"session_id": str}`
- Loads session from Redis, passes full session dict to `stream_interview_questions()`
- Returns `StreamingResponse` (same SSE format as existing streams)

5. **Add new endpoint `POST /api/generate-pdf`:**
- Accepts `GeneratePdfRequest`
- Loads session from Redis, validates session exists
- Calls `generate_pdf_report_in_memory(form=session_data, qa_pairs=request.qa_pairs, lang=session_data["lang"])`
- Returns `Response` with `application/pdf` content type
- No LLM call whatsoever

6. **Do NOT delete old endpoints yet** (`/initial-questions-stream`, `/follow-up-questions-stream`, `/summarize-and-generate-pdf`). They are removed in Sprint 3.

### Changes to `agent_service.py`

Add alongside the existing functions (do not delete anything yet):

```python
def get_interview_chain() -> Runnable:
    """Single interview chain. Receives full form context, generates up to 5 targeted questions."""
    # Build ChatPromptTemplate with system prompt from PRD Section 5.1
    # Human message must include ALL form fields as template variables
    # See PRD docs/PRD.md Section 5.1 for full system prompt text

async def stream_interview_questions(
    session_data: dict,
    lang: str,
    chain: Runnable
) -> AsyncGenerator[str, None]:
    """Streams questions from the interview chain."""
```

The interview chain prompt must include ALL form fields from the session schema. See `docs/PRD.md` Section 5.1 for the exact system prompt and rules.

### Tests to write in `test_api_integration.py`

Add these tests (keep all existing tests for now):

```python
def test_init_session_with_full_form(mock_create):
    # POST /api/session/init with full form payload
    # Assert 200, session_id returned
    # Assert mock_create called with dict containing age_bracket, sex, specialist, etc.

def test_interview_questions_stream(mock_get, mock_stream):
    # Mock get_session to return a full session dict
    # Mock stream_interview_questions to yield "1. Question?"
    # POST /api/interview-questions-stream with {"session_id": "fake-id"}
    # Assert 200, SSE data contains "Question"

def test_interview_stream_session_not_found(mock_get):
    # Mock get_session to return {}
    # Assert 404

def test_generate_pdf_with_qa_pairs(mock_get):
    # Mock get_session to return full session dict
    # POST /api/generate-pdf with session_id + qa_pairs=[{question, answer}]
    # Assert 200, content-type application/pdf, content starts with b"%PDF-"
    # Assert NO call to any LLM function (verify summarize_and_structure_anamnesis NOT called)

def test_generate_pdf_session_not_found(mock_get):
    # Mock get_session to return {}
    # Assert 404
```

### Done criteria
- [ ] All 5 new tests pass
- [ ] All previously passing tests still pass
- [ ] `test_security.py` passes

---

## Sprint 2 — Deterministic PDF Service

**Goal:** Rewrite `pdf_service.py` to accept the new two-source data model (structured form + Q&A pairs). No LLM output consumed. This sprint is independent of Sprint 3.

### Read first
- `src/preconsult/services/pdf_service.py` (full file)
- `tests/test_pdf_service.py` (full file)
- `docs/PRD.md` Section 5.2 (PDF Template Specification)

### New signature

```python
def generate_pdf_report_in_memory(
    form: dict,
    qa_pairs: list,   # list of QAPair objects or dicts with "question"/"answer" keys
    lang: str = "en"
) -> tuple[bytes, str]:
```

### PDF layout (two sections)

**Section 1 — Patient Summary** (from `form` dict):
```
Disclaimer (top, hardcoded)
Title: "Your Health Summary" / "Seu Resumo de Saúde"

Appointment:               form["specialist"]
Age bracket:               form["age_bracket"]
Biological sex:            form["sex"]

Chief Complaint:           form["chief_complaint"]
Duration:                  form["duration"]
Details:                   form.get("complaint_detail") or "None reported"

Pre-existing conditions:   ", ".join(form["conditions"]) or "None reported"
Current medications:       ", ".join(form["medications"]) or "None reported"
Drug allergies:            form.get("allergies") or "None reported"
Family history:            ", ".join(form["family_history"]) or "None reported"
Smoking:                   form["smoking"]
Alcohol:                   form["alcohol"]
```

**Section 2 — Clinical Questions & Patient Answers** (from `qa_pairs`):
```
Section header: "Clinical Questions & Patient Answers"

Q1: qa_pairs[0]["question"]
A:  qa_pairs[0]["answer"]

Q2: qa_pairs[1]["question"]
A:  qa_pairs[1]["answer"]

[... up to Q5]
```

### i18n additions to `pdf_service.py` `translations` dict

Add to both `"en"` and `"pt"` dicts:
```python
# English additions
"appointment": "Appointment",
"age_bracket": "Age bracket",
"sex": "Biological sex",
"duration": "Duration",
"complaint_detail": "Additional details",
"conditions": "Pre-existing conditions",
"medications": "Current medications",
"allergies": "Drug allergies",
"family_history": "Family history",
"smoking": "Smoking",
"alcohol": "Alcohol",
"qa_section_title": "Clinical Questions & Patient Answers",
"question_label": "Q",
"answer_label": "A",
"none_reported": "None reported",

# Portuguese additions
"appointment": "Consulta",
"age_bracket": "Faixa etária",
"sex": "Sexo biológico",
"duration": "Duração",
"complaint_detail": "Detalhes adicionais",
"conditions": "Condições pré-existentes",
"medications": "Medicamentos em uso",
"allergies": "Alergias a medicamentos",
"family_history": "Histórico familiar",
"smoking": "Tabagismo",
"alcohol": "Álcool",
"qa_section_title": "Perguntas Clínicas e Respostas do Paciente",
"question_label": "P",
"answer_label": "R",
"none_reported": "Não informado",
```

### Tests — delete all existing tests, write these instead

```python
def test_pdf_valid_bytes_en():
    # Call with minimal valid form + 1 qa_pair, lang="en"
    # Assert bytes start with b"%PDF-"
    # Assert filename == "Medical_Summary_Report.pdf"

def test_pdf_valid_bytes_pt():
    # Call with minimal valid form + 1 qa_pair, lang="pt"
    # Assert bytes start with b"%PDF-"
    # Assert filename == "Resumo_Medico.pdf"

@patch("...canvas.Canvas")
def test_pdf_renders_form_section(mock_canvas_class):
    # Provide form with known values (specialist="Cardio", chief_complaint="chest pain")
    # Assert drawString called with text containing "Cardio" and "chest pain"

@patch("...canvas.Canvas")
def test_pdf_renders_qa_section(mock_canvas_class):
    # Provide qa_pairs=[{"question": "How severe?", "answer": "Very bad"}]
    # Assert drawString called with text containing "How severe?" and "Very bad"

@patch("...canvas.Canvas")
def test_pdf_none_reported_for_empty_lists(mock_canvas_class):
    # Provide form with conditions=[], medications=[], family_history=[]
    # Assert "None reported" (or PT equivalent) appears in drawn strings

def test_pdf_empty_qa_pairs_does_not_crash():
    # qa_pairs=[] should return valid PDF bytes without Q&A section
    # (defensive: form is still rendered)

@patch("...canvas.Canvas")
def test_pdf_pagination_long_answer(mock_canvas_class):
    # Provide qa_pairs with very long answer text ("word " * 500)
    # Assert mock_canvas.return_value.showPage.call_count >= 1

def test_pdf_unknown_lang_defaults_to_en():
    # lang="xx" should not raise, should use English labels
```

### Done criteria
- [ ] All 7 new tests pass
- [ ] Old `test_api_integration.py::test_generate_pdf_with_qa_pairs` goes green (calls real pdf_service)
- [ ] `test_security.py` passes

---

## Sprint 3 — Agent Service: Single Interview Chain

**Goal:** Replace the two-chain OPQRST+SAMPLE architecture with one interview chain receiving full form context. Add emergency detection. Remove dead code.

### Read first
- `src/preconsult/services/agent_service.py` (full file)
- `src/preconsult/api/endpoints.py` (full file)
- `tests/test_agent_service.py` (full file)
- `docs/PRD.md` Section 5.1 (full system prompt and rules)

### Changes to `agent_service.py`

**Add** new function `get_interview_chain()` using `ChatPromptTemplate` with:
- System prompt from `docs/PRD.md` Section 5.1 (copy verbatim — it contains 7 strict rules including emergency detection)
- Human message template that includes ALL form fields as template variables: `{age_bracket}`, `{sex}`, `{specialist}`, `{chief_complaint}`, `{duration}`, `{complaint_detail}`, `{conditions}`, `{medications}`, `{allergies}`, `{family_history}`, `{smoking}`, `{alcohol}`, `{language_instruction}`

**Add** `stream_interview_questions(session_data: dict, lang: str, chain: Runnable)` that:
- Builds the input dict from session_data, adding `language_instruction` from `get_language_instructions(lang)`
- Streams chunks from `chain.astream(input_dict)`

**Delete** (after adding replacements):
- `get_initial_agent_chain()`
- `get_follow_up_agent_chain()`
- `get_structuring_chain()`
- `stream_initial_questions()`
- `stream_follow_up_questions()`
- `summarize_and_structure_anamnesis()`
- The `_follow_up_agent_chain` and `_structuring_chain` singletons

### Changes to `endpoints.py`

**Wire** `/api/interview-questions-stream` (added in Sprint 1) to the new `get_interview_chain()` via `Depends`.

**Delete** these endpoints and their Pydantic models:
- `POST /api/follow-up-questions-stream` (and `FollowUpRequest`)
- `POST /api/summarize-and-generate-pdf` (and `SummarizationRequest`)

Also delete the `get_initial_agent_chain` and `get_follow_up_agent_chain` imports.

The old `/api/initial-questions-stream` endpoint: **repurpose it** to call `stream_interview_questions` instead of the old OPQRST chain, or delete it if the frontend migration in Sprint 4 is imminent. Safest: keep the route path but change its implementation to call the new chain (zero frontend change needed until Sprint 4).

### Tests — delete all existing tests, write these instead

```python
def test_language_instructions_en():
    # Assert "English" in instructions["initial_q_instruction"]
    # Assert "not mentioned" in instructions["not_mentioned"].lower()

def test_language_instructions_pt():
    # Assert "Português" in instructions["initial_q_instruction"]
    # Assert "não mencionado" in instructions["not_mentioned"].lower()

@pytest.mark.asyncio
@patch("...get_llm")
async def test_interview_chain_streams_questions(mock_get_llm):
    # FakeListChatModel(responses=["1. Question A?\n2. Question B?"])
    # Build minimal session_data dict with all required form fields
    # stream_interview_questions(session_data, "en", chain)
    # Assert "Question A" in joined output

@pytest.mark.asyncio
@patch("...get_llm")
async def test_interview_chain_pt(mock_get_llm):
    # Same as above with lang="pt"
    # Assert chain was invoked (mock_get_llm.called)

def test_interview_chain_prompt_contains_all_form_fields():
    # Call get_interview_chain() — do NOT mock the LLM, just inspect the chain
    # chain.steps[0] is the prompt template
    # Assert all required input variables present:
    # age_bracket, sex, specialist, chief_complaint, duration,
    # conditions, medications, allergies, family_history, smoking, alcohol

def test_interview_prompt_contains_emergency_rule():
    # Read agent_service.py source (or inspect chain prompt messages)
    # Assert "emergency" in the system prompt text (case-insensitive)
    # Assert "do not generate questions" in the system prompt text (case-insensitive)

@pytest.mark.asyncio
@patch("...get_llm")
async def test_emergency_detection_in_output(mock_get_llm):
    # FakeListChatModel(responses=["⚠️ EMERGENCY: Please call 911 immediately."])
    # session_data with chief_complaint containing "severe chest pain"
    # Assert output contains "EMERGENCY" or "emergency" or "911" or "immediate"
    # Assert output does NOT start with "1." (no questions generated)
```

### Tests to delete from `test_api_integration.py`
- `test_initial_questions_stream`
- `test_follow_up_questions_stream`
- `test_summarize_and_generate_pdf`

### Done criteria
- [ ] All 6 new agent tests pass
- [ ] All 5 Sprint 1 API tests still pass
- [ ] `test_security.py` passes
- [ ] `test_session_service.py` passes (unchanged)
- [ ] No import of deleted functions anywhere in codebase

---

## Sprint 4 — Frontend: Steps 3 & 4 + New Flow

**Goal:** Add the two missing form steps and wire the Reflex frontend to the new backend endpoints.

### Read first
- `reflex_app/securemed/securemed.py` (full file)
- `reflex_app/securemed/state.py` (full file)
- `reflex_app/securemed/i18n.py` (full file)
- `docs/PRD.md` Section 4 (full UX flow spec with field specs)

### Changes to `state.py`

**New state fields** (add, keep `age`, `gender`, `lang`, `session_id`, `step`, `loading`):
```python
# Step 2 additions
specialist: str = ""
age_bracket: str = "26-35"
duration: str = ""
complaint_detail: str = ""
# Step 3
conditions: list[str] = []
medications: list[str] = []
allergies_flag: bool = False
allergies_text: str = ""
# Step 4
family_history: list[str] = []
smoking: str = ""
alcohol: str = ""
# Interview Q&A (replaces initial_answers / follow_up_answers)
questions: list[str] = []
current_answers: list[str] = []
```

**Remove:** `initial_answers`, `follow_up_answers`, `initial_questions_text`, `follow_up_questions_text`

**Update `init_session()`:**
- Now fires after Step 4 (called from Step 4's "Continue" button)
- Sends ALL form fields to `POST /api/session/init`
- On success: `self.step = 5` and triggers `get_interview_questions()`

**Replace `get_initial_questions()` with `get_interview_questions()`:**
- Calls `POST /api/interview-questions-stream`
- Parses each SSE line, splits response into individual questions
- Stores in `self.questions`
- Initializes `self.current_answers` as list of empty strings (same length)

**Replace `submit_initial_answers()` + `submit_follow_up_answers()` with `submit_answers()`:**
- Validates all questions have answers
- Moves to the summary step

**Update `download_report()`:**
- Sends `POST /api/generate-pdf` with `session_id` + `qa_pairs`
- `qa_pairs` built from `zip(self.questions, self.current_answers)`

**Add helpers:**
```python
def toggle_condition(self, condition: str): ...   # add/remove from self.conditions
def toggle_family_history(self, item: str): ...   # add/remove from self.family_history
def add_medication(self): ...                     # append "" to self.medications
def update_medication(self, idx: int, val: str): ...
def remove_medication(self, idx: int): ...
def set_answer(self, idx: int, val: str): ...     # update self.current_answers[idx]
```

### Changes to `securemed.py`

**Add components (see PRD Section 4 for field specs):**

```python
def step_2_chief_complaint() -> rx.Component:
    # specialist text input
    # chief_complaint textarea (max 500 chars)
    # duration chips: "Started today" / "A few days" / "Weeks" / "Months" / "Years"
    # complaint_detail textarea (optional, label: "Can you add more detail?")
    # "Continue" button → State.go_to_step_3

def step_3_history() -> rx.Component:
    # Checkboxes for: Hypertension, Diabetes, Asthma/Bronchitis,
    #   Depression/Anxiety, Thyroid issues, + "Other (type)" text
    # Dynamic medication list with "+ Add medication" and remove buttons
    # Allergies radio (Yes/No) — reveals text input on "Yes"
    # "Continue" button → State.go_to_step_4

def step_4_lifestyle() -> rx.Component:
    # Checkboxes for: Cancer, Heart disease, Diabetes, Alzheimer's
    # Smoking radio: Currently smoke / Former smoker / Never smoked
    # Alcohol radio: Rarely / Socially / Frequently / Never
    # "Generate My Questions" button → State.init_session (fires the LLM call)

def step_5_interview_qs() -> rx.Component:
    # Shows each question with a textarea for the answer
    # State.questions renders dynamically (up to 5)
    # "Generate My Summary" button → State.submit_answers
```

**Update `stepper_component()`:** Change `range(4)` to `range(6)` (6 steps: 0=intake, 1=chief complaint, 2=history, 3=lifestyle, 4=interview, 5=summary).

**Update `rx.match` in `index()`** to handle all steps 0–5.

**Update `step_0_demographics()`:** Remove `chief_complaint` textarea and `start_btn` — Step 0 now only collects age bracket (chips, not number input) and sex. "Continue" button → `State.go_to_step_1`.

**Age bracket chips** (replaces `rx.input(type="number")`):
```python
rx.hstack(
    *[rx.button(bracket, on_click=State.set_age_bracket(bracket),
                variant=rx.cond(State.age_bracket == bracket, "solid", "outline"))
      for bracket in ["18-25", "26-35", "36-45", "46-60", "60+"]]
)
```

### Changes to `i18n.py`

Add keys for all new fields. At minimum:
```python
"specialist", "specialist_ph",
"duration", "duration_opts" (list of 5 options),
"complaint_detail", "complaint_detail_ph",
"conditions_label", "conditions_opts" (list of 5 + Other),
"medications_label", "medications_ph", "add_medication",
"allergies_label", "allergies_yes", "allergies_no", "allergies_ph",
"family_history_label", "family_history_opts" (list of 4),
"smoking_label", "smoking_opts" (list of 3),
"alcohol_label", "alcohol_opts" (list of 4),
"step_3_desc", "step_4_desc",  # empathetic microcopy
"step_names" → update to 6 names,
```

### No automated tests (Reflex has no unit test framework)

**Manual test checklist — complete all before marking sprint done:**
```
□ Step 0: Age bracket chips select/deselect correctly; sex radio works
□ Step 0 → Step 1 navigation; stepper shows correct active step
□ Step 1: Specialist, chief complaint, duration chips, detail field all bind to state
□ Step 2: Each condition checkbox adds/removes from state.conditions
□ Step 2: "+ Add medication" appends a field; remove button removes it
□ Step 2: Allergies "No" → text field hidden; "Yes" → text field visible
□ Step 3: Each family history checkbox adds/removes from state.family_history
□ Step 3: Smoking and alcohol radios bind to state
□ Step 3 "Generate My Questions" → loading state shown → questions appear
□ Step 4: Each question has its own textarea; answers bind to state
□ "Generate My Summary" → loading → step 5 (summary screen)
□ "Download PDF" → PDF downloaded; contains form data AND Q&A section
□ Stepper shows 6 steps with correct labels throughout
□ Both EN and PT languages display correctly
□ Back-navigation preserves all entered data
```

---

## Sprint 5 — Fixes: Three Missing "Done" Features

**Goal:** Implement the three features that were marked "Done" in the PRD but never built. Small sprint.

### Read first
- `reflex_app/securemed/securemed.py` — `step_3_summary()` component (the final export screen)
- `reflex_app/securemed/i18n.py` — `complete_desc` and `complete_title` keys
- `reflex_app/securemed/state.py` — `download_report()` handler
- `tests/test_security.py` (full file)
- `docs/PRD.md` Epic 2.3, 3.3, 3.4 for acceptance criteria

### Fix 1 — Copy to Clipboard (Epic 3.3)

In `securemed.py` final step component, add a "Copy" button after the download button:

```python
rx.button(
    State.t["copy_btn"],
    on_click=rx.set_clipboard(State.summary_text),
    color_scheme="blue",
    variant="outline",
    size="3",
    width="100%",
    aria_label="Copy summary to clipboard"
)
```

Add `summary_text: str = ""` to `state.py`. Populate it in `submit_answers()` by formatting the form + Q&A into plain text (same content as PDF, text format).

In `i18n.py` add: `"copy_btn"` (EN: "Copy to Clipboard", PT: "Copiar para a Área de Transferência") and `"copy_success"`.

**Acceptance criterion:** Button visible on final step; clicking it places text on clipboard on both desktop and mobile.

### Fix 2 — Auto-Destruction Notice (Epic 3.4)

In `i18n.py`, update `complete_desc` for both languages to explicitly state data deletion:
- EN: `"Your summary is ready. Once you close this window, all data is permanently deleted from our servers."`
- PT: `"Seu resumo está pronto. Ao fechar esta janela, todos os dados serão permanentemente apagados dos nossos servidores."`

**Acceptance criterion:** The word "deleted" (EN) or "apagados" (PT) appears on the final screen.

### Fix 3 — Emergency Detection (Epic 2.3)

This was addressed in Sprint 3 (rule added to prompt). Verify end-to-end:
- Test the live app with chief complaint: "I have severe chest pain and can't breathe"
- Expected: questions step shows an emergency warning, not numbered questions

### New tests in `test_security.py`

```python
def test_auto_destruction_notice_en():
    from reflex_app.securemed.i18n import translations
    assert "deleted" in translations["en"]["complete_desc"].lower()

def test_auto_destruction_notice_pt():
    from reflex_app.securemed.i18n import translations
    assert "apagados" in translations["pt"]["complete_desc"].lower()

def test_emergency_rule_in_interview_prompt():
    import inspect
    from preconsult.services.agent_service import get_interview_chain
    # Inspect the prompt template's system message
    chain = get_interview_chain()
    prompt = chain.steps[0]  # or however the chain is structured
    system_msg = str(prompt.messages[0])
    assert "emergency" in system_msg.lower()
    assert "do not generate questions" in system_msg.lower()
```

Also add to `test_api_integration.py`:

```python
def test_full_session_happy_path(mock_create, mock_get, mock_stream, mock_pdf):
    # 1. POST /session/init with full form → 200, session_id
    # 2. POST /interview-questions-stream with session_id → 200, SSE with questions
    # 3. POST /generate-pdf with session_id + qa_pairs → 200, PDF bytes
    # Assert each step returns expected status and content type
    # Assert no LLM call made in step 3 (generate-pdf)
```

### Done criteria
- [ ] Copy to Clipboard button visible and functional on final step
- [ ] Both language `complete_desc` values contain deletion notice
- [ ] 3 new `test_security.py` tests pass
- [ ] `test_full_session_happy_path` passes
- [ ] All prior tests still pass

---

## Sprint 6 — UX Polish

**Goal:** Complete Epic 4. No new backend tests. Visual verification only.

### Read first
- `reflex_app/securemed/securemed.py` (full file)
- `reflex_app/securemed/i18n.py`
- `docs/PRD.md` Epic 4 (items 4.2–4.5)

### 4.1 — Stepper: already shipped, update status in PRD
Change Epic 4.1 status from "To do" to "Done" in `docs/PRD.md`.

### 4.2 — Trust microcopy
Ensure every step has an empathetic `rx.text()` subtitle using a `_desc` i18n key. Steps 3 and 4 were added in Sprint 4; verify the copy is present and meaningful. Suggested copy:
- Step 3 desc: "This helps us avoid asking about things you've already told us."
- Step 4 desc: "A few more questions to give your doctor the full picture."

### 4.3 — Entrance animations (staggered)
Current code has `animation="fadeIn 0.5s ease-out"` on each step component. Upgrade to staggered:
```python
# Title: delay 0s
# Input group 1: delay 0.1s
# Input group 2: delay 0.2s
# Button: delay 0.3s
```
Add CSS in the global `style` dict:
```python
"@keyframes fadeInUp": {
    "from": {"opacity": "0", "transform": "translateY(16px)"},
    "to": {"opacity": "1", "transform": "translateY(0)"}
}
```
Apply `animation="fadeInUp 0.4s ease-out {delay}s both"` per element.

### 4.4 — Mobile touch targets
Audit all buttons and inputs. Add `min_height="44px"` to any element that doesn't already meet this threshold. Chips (age bracket, duration, condition checkboxes) need at least `padding="0.75em 1em"`.

### 4.5 — Accessibility & contrast
- Ensure all inputs added in Sprint 4 have `aria_label` attributes
- Increase placeholder opacity in glass inputs:
  ```python
  style={"::placeholder": {"color": "rgba(255,255,255,0.6)"}}
  ```

### Manual verification checklist
```
□ Each step has a visible, empathetic subtitle
□ Each step entrance has staggered animation (title → fields → button)
□ All inputs/buttons have min height 44px on 375px wide viewport (iPhone SE)
□ Placeholder text visible against glassmorphism background
□ Tab navigation through all form fields works logically
□ Screen reader announces all labels (test with VoiceOver or NVDA)
```

### Done criteria
- [ ] All manual checklist items checked
- [ ] Epic 4.1 status updated to "Done" in `docs/PRD.md`
- [ ] All backend tests still pass (no regressions from frontend changes)
