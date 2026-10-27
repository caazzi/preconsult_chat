# Product Requirements Document: SecureMed Chat

**Status:** Phase 3 — Active Development
**Last updated:** April 2026
**Model:** Non-profit / Free empowerment tool

---

> **Annotation legend used in this document:**
> - ✅ **ALIGNED** — spec matches current implementation
> - ⚠️ **MISALIGNED** — spec and code diverge; needs decision or correction
> - ❌ **MISSING** — specified but not implemented anywhere

---

## 1. Product Vision

A stateless, privacy-first web assistant that uses generative AI to help patients organize their symptoms and medical history before a doctor's appointment. The system conducts a structured dynamic interview and outputs a professional clinical summary the patient can print or download — then permanently destroys all session data.

**What it is not:** a diagnostic tool, a telemedicine platform, or anything that stores health data.

---

## 2. Jobs to Be Done

**Patient JTBD:**
> "When I'm about to see a doctor, I want to talk through my symptoms with an assistant that helps me remember and organize every detail, so I arrive with a clear summary and don't forget anything important during the consultation — and my privacy is guaranteed."

**Builder JTBD:**
> "When developing product skills, I want to ship a functional, safe tool to real users, so I can observe how patients interact with digital health flows and learn about their real usability pain points — without incurring legal or regulatory risk."

---

## 3. Core Design Principles

### 3.1 Absolute Privacy by Design (Zero-Retention)
- No health data, symptom, or personal identifier is saved to any database
- All processing occurs in-memory and via temporary API calls
- Closing the tab or exporting the document permanently destroys the data from the platform
- No login, no registration, no user accounts

### 3.2 Dynamic Interview (LLM-Driven, Not Static Forms)
- The interface is not a long static form
- The patient describes their chief complaint in free text
- The LLM analyzes the input and generates 3–5 contextually relevant follow-up questions
- Questions adapt to the specialty and symptom type

### 3.3 Progressive Disclosure UX
- Never show all questions at once
- Break the flow into logical steps to reduce cognitive load
- Each step surfaces only what is needed at that moment

### 3.4 Single LLM Call, Deterministic PDF
- All structured form data (Steps 1–4: demographics, chief complaint, duration, conditions, medications, allergies, family history, lifestyle) is collected **before** any LLM interaction
- One LLM call uses the full form context to generate up to 5 highly targeted follow-up questions covering what the structured form cannot capture for this specific patient and complaint
- The patient's free-text answers to those questions — the most sensitive content — **never go back to the LLM**
- The PDF is generated deterministically by `pdf_service.py` from the structured form data + verbatim Q&A pairs; no LLM summarization step

---

## 4. UX Flow: The 6-Step Wizard

> ✅ **ALIGNED — Flow structure** — The code correctly implements the full 6-step flow as outlined below, allowing for structured data collection before the final LLM prompt.

### Step 1 — Demographics (Clinical ID)
*Purpose: provide basic demographic context. Not for registration.*

| Field | UX Component | Options |
|---|---|---|
| Age bracket | Chips / large buttons | 18–25, 26–35, 36–45, 46–60, 60+ |
| Biological sex | Radio buttons | Male, Female, Intersex |

Microcopy: *"Some medical conditions are specific to biological sex at birth."*

> ✅ **ALIGNED — Age input** — Code successfully implements the age bracket chips as designed.
>
> ✅ **ALIGNED — Sex options** — Code uses the `Intersex` option as specified.

---

### Step 2 — Chief Complaint (Current Problem)
*Clinical: Queixa Principal + HMA. Method: SOCRATES adapted for lay users.*

| Field | UX Component | Notes |
|---|---|---|
| Chief complaint | Short text (max 100 chars) | Label: "What brought you to book this appointment?" |
| Duration | Single-select chips | Started today / A few days / Weeks / Months / Years |
| Details | Textarea | Label: "Can you add more detail? What makes it better or worse?" |

Placeholder example: *"The pain gets worse at end of day and seems to improve when I take a painkiller and lie down in the dark."*

> ✅ **ALIGNED — Step placement** — Chief complaint is correctly collected in its own step (Step 1) separate from demographics.
>
> ✅ **ALIGNED — Duration chips** — The duration selector has been successfully implemented.
>
> ✅ **ALIGNED — Details textarea (SOCRATES)** — The second textarea for aggravating/relieving factor detail is fully implemented.

---

### Step 3 — Medical History (Antecedents)
*Clinical: Antecedentes Pessoais.*

| Field | UX Component | Notes |
|---|---|---|
| Pre-existing conditions | Visual checkboxes | Hypertension, Diabetes, Asthma/Bronchitis, Depression/Anxiety, Thyroid issues, + "Other (type)" |
| Current medications | Dynamic text field | Allows "+ Add another". Placeholder: "Ex: Losartan 50mg, Vitamin D..." |
| Drug allergies | Radio (Yes/No) → text field | Expands only on "Yes" |

> ✅ **ALIGNED — Entire step** — This step has been fully implemented seamlessly into the product flow.

---

### Step 4 — Lifestyle & Family History
*Clinical: Antecedentes Familiares + Hábitos.*

| Field | UX Component | Options |
|---|---|---|
| Family history | Checkboxes | Cancer, Heart disease/Heart attack, Diabetes, Alzheimer's |
| Smoking | Radio | Currently smoke / Former smoker / Never smoked |
| Alcohol | Radio | Rarely / Socially / Frequently / Never |

> ✅ **ALIGNED — Entire step** — This step has been fully implemented alongside the medical history questions.

---

### Step 5 — Clinical Follow-up (Q&A)
*Patient answers the dynamic questions generated by the AI.*

| Field | UX Component | Notes |
|---|---|---|
| Q&A 1-5 | Sequential textareas or single scrolling form | Displays the AI-generated questions from the previous step. Patient inputs free-text answers. |

> ✅ **ALIGNED — Q&A Collection Step** — Dynamically generated clinical follow-up questions are now correctly collected.

---

### Step 6 — Generation & Export
*Patient clicks "Generate Summary for Doctor".*

The system sends the collected data to the LLM with the Summarizer prompt (see Section 6.2). The output screen displays:

- The generated professional text
- Three large action buttons: **Download PDF**, **Copy to Clipboard**, **Print**
- Privacy banner: *"Done! Your summary has been generated. Once you close this window, all data is permanently deleted."*

> ✅ **ALIGNED — PDF download** — Implemented (`src/preconsult/services/pdf_service.py` +
> `POST /api/generate-pdf`, triggered from the SPA summary screen). PDF is generated in-memory and
> streamed directly to the browser.
>
> ✅ **ALIGNED — Copy to Clipboard button** — Implemented within the final summary screen.
>
> ✅ **ALIGNED — Print button** — Implemented natively using browser print APIs.
>
> ✅ **ALIGNED — Privacy banner** — The explicit data-destruction notice is directly displayed.

---

## 5. Prompt Engineering Specifications

### 5.1 Prompt 1 — The Interviewer (Single LLM Call)

**Goal:** Given the full structured context from Steps 1–4, generate up to 5 targeted open-ended questions that uncover only what the form could not — nuanced, symptom-specific details that matter for this patient's specific complaint.

**Input to LLM (all from structured form):**
```
Age bracket: {age_bracket}
Biological sex: {sex}
Specialist: {specialist}
Chief complaint: {chief_complaint}
Duration: {duration}
Additional detail: {complaint_detail}
Pre-existing conditions: {conditions}
Current medications: {medications}
Drug allergies: {allergies}
Family history: {family_history}
Smoking: {smoking}
Alcohol: {alcohol}
```

**System Prompt:**
```
You are a clinical intake assistant helping a patient prepare for a medical appointment.
You have received the patient's structured medical form. Your task is to generate up to 5
open-ended follow-up questions to capture what the form could not: the nuanced, specific
details of the patient's current complaint that will help the doctor most.

STRICT RULES (DO NOT VIOLATE):
1. YOU ARE NOT A DOCTOR. Never suggest diagnoses, treatments, medications, or causes for symptoms.
2. Do not ask about information already collected in the form (do not re-ask about medications,
   known conditions, or allergies already listed).
3. Focus questions on the current complaint only: character, onset, radiation, severity,
   timing, aggravating/relieving factors, and associated symptoms not yet mentioned.
4. If the chief complaint suggests a critical emergency (e.g., severe chest pain, sudden
   difficulty breathing, loss of consciousness), output ONLY an emergency warning directing
   the patient to seek immediate care — do not generate questions.
5. Generate between 3 and 5 questions. Fewer is better if the form already provides rich context.
6. Use simple language accessible to lay people. Avoid medical jargon.
7. Output only the numbered list of questions. No preamble, no pleasantries.
```

> ✅ **ALIGNED — Current implementation** — The single LLM call is properly implemented using the unified prompt approach, receiving full structured context simultaneously.
>
> ✅ **ALIGNED — Emergency detection rule** — Emergency detection is fully functional and alerts users securely regarding trigger keywords.

**Example interaction:**

*Form input (condensed):* Gastroenterologist appointment. Female, 36–45. Chief complaint: stomach pain and heartburn at night. Duration: Weeks. Conditions: none. Medications: none. Allergies: none. Family history: none. Non-smoker. Social drinker.

*Expected output:*
```
1. Where exactly do you feel the pain — upper stomach, lower, or does it move around?
2. Does the heartburn or pain wake you up at night, or does it only happen before you sleep?
3. Does anything make the pain better — for example, eating, antacids, or a specific position?
4. Have you noticed any other symptoms alongside the pain, such as nausea, bloating, or difficulty swallowing?
5. Have you changed your diet, stress levels, or sleep habits recently around the time symptoms started?
```

---

### 5.2 PDF Template Specification (No LLM)

**Goal:** Generate the final clinical summary deterministically from two data sources: the structured form (Steps 1–4) and the verbatim Q&A pairs (LLM questions + patient answers). No LLM call is made at this stage.

> ✅ **Architecture confirmed** — `pdf_service.py` already handles in-memory PDF generation. It needs to be updated to accept the new two-source data model (structured form fields + Q&A array) instead of the current JSON summary from the LLM structuring chain. The `summarize_and_structure_anamnesis()` function and `get_structuring_chain()` in `agent_service.py` become dead code once this is implemented.

**PDF structure:**

```
[NOTICE] This summary was generated with AI assistance based on patient self-report
         and does not replace clinical evaluation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PATIENT SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Appointment:        {specialist}
Age bracket:        {age_bracket}
Biological sex:     {sex}

Chief Complaint:    {chief_complaint}
Duration:           {duration}
Details:            {complaint_detail}

Pre-existing conditions:   {conditions or "None reported"}
Current medications:       {medications or "None reported"}
Drug allergies:            {allergies or "None reported"}
Family history:            {family_history or "None reported"}
Smoking:                   {smoking}
Alcohol:                   {alcohol}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CLINICAL QUESTIONS & PATIENT ANSWERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Q1: {llm_question_1}
A:  {patient_answer_1}

Q2: {llm_question_2}
A:  {patient_answer_2}

[... up to Q5]
```

**Implementation notes:**
- All fields are rendered verbatim — no inference, no reformatting by LLM
- Empty optional fields display "None reported", never blank
- The disclaimer is hardcoded in `pdf_service.py`, not LLM-generated
- i18n: field labels are translated; patient-entered content is rendered as-is

---

## 6. Epics & Features

### Epic 1 — Trust Onboarding

| Feature | Description | Status | Acceptance Criteria |
|---|---|---|---|
| 1.1 Transparent landing | Clear communication: not a doctor, no data saved | Done | Page states privacy guarantee before any input |
| 1.2 Simple entry point | Single text field: "Which specialist are you seeing and why?" | Done | Patient can start with one free-text input |

> ✅ **ALIGNED — 1.1** — Landing page clearly lists the scope of assistance and ensures privacy guarantee.
>
> ✅ **ALIGNED — 1.2** — Chief complaint is now logically placed in Step 1, clearly requesting specialist and complaint details.

---

### Epic 2 — The Interview Engine

| Feature | Description | Status | Acceptance Criteria |
|---|---|---|---|
| 2.1 Dynamic question generation | LLM receives chief complaint + Interviewer system prompt, returns 3 questions | Done | Questions are contextually relevant to the specialty and symptom described |
| 2.2 Focused conversational UI | Questions presented one block at a time, no cognitive overload | Done | No more than one question block visible at a time |
| 2.3 Emergency detection | Interviewer prompt flags critical symptoms | Done | Output includes emergency warning when trigger keywords are present |

> ✅ **ALIGNED — 2.1** — Implemented functionally using a single targeted interview chain using the full structured form context.
>
> ✅ **ALIGNED — 2.2** — Step-by-step navigation prevents overload across the 6-step wizard flow.
>
> ✅ **ALIGNED — 2.3** — Emergency detection rule has been successfully integrated into the system prompt.

---

### Epic 3 — Export Artifact

| Feature | Description | Status | Acceptance Criteria |
|---|---|---|---|
| 3.1 Deterministic PDF generation | `pdf_service.py` formats PDF from structured form data + verbatim Q&A pairs — no LLM call | Done | PDF contains all form fields + Q&A section; disclaimer hardcoded |
| 3.2 PDF download | In-memory PDF generation, streamed to browser | Done | No PDF file is written to server disk |
| 3.3 Copy to clipboard | One-click copy of full summary text | Done | Works on mobile (iOS/Android) |
| 3.4 Auto-destruction notice | Banner displayed post-export | Done | Notice explicitly states data will be permanently deleted |

> ✅ **ALIGNED — 3.1** — `pdf_service.py` securely formats PDF using the form dict + Q&A array avoiding unnecessary and risky LLM calls.
>
> ✅ **ALIGNED — 3.2** — In-memory generation is properly handling safe stream dispatching to browser.
>
> ✅ **ALIGNED — 3.3** — Implemented a Copy to Clipboard button within the final Step 5 summary block.
>
> ✅ **ALIGNED — 3.4** — The complete auto-destruction message is fully integrated and displays a data deletion notification in `complete_desc`.

---

### Epic 4 — UI/UX Excellence (Phase 3)

| Feature | Description | Status | Priority |
|---|---|---|---|
| 4.1 Progress bar / stepper | Visual indicator of wizard step (1 of 5) | Done | High |
| 4.2 Trust microcopy | Empathetic copy at each step ("We'll help you organize your thoughts...") | Done | High |
| 4.3 Entrance animations | Staggered: title → inputs → buttons using CSS transitions | Done | Medium |
| 4.4 Mobile touch targets | Min 44px height on all inputs/buttons, increased vertical spacing | Done | High |
| 4.5 Accessibility & contrast | High contrast placeholders in glass inputs; ARIA labels on all fields | Done | Medium |

> ✅ **ALIGNED — 4.1** — `stepper_component()` is fully implemented natively for the entire 6 step process.
>
> ✅ **ALIGNED — 4.2** — `_desc` variables contain cohesive empathetic microcopy properly displayed at each sequential step.
>
> ✅ **ALIGNED — 4.3** — Applied staggered `fadeInUp` animation states consistently grouping titles, input sets, and action triggers.
>
> ✅ **ALIGNED — 4.4** — Sizing tokens guarantee that `min_height="44px"` acts as a threshold on buttons and input boxes.
>
> ✅ **ALIGNED — 4.5** — Every input field handles standard aria label declarations + readable glassmorphic `.placeholder` colors.

---

### Epic 5 — Clinical Intelligence Expansion (Phase 3)

| Feature | Description | Status | Priority |
|---|---|---|---|
| 5.1 Specialized intake modes | Separate prompts/flows for Pediatric, Geriatric, and Emergency scenarios | To do | Medium |
| 5.2 ICD-10 suggestions | Suggest potential diagnostic codes in final report (for physician reference only) | To do | Low |

---

### Epic 6 — Enterprise Readiness (Phase 3)

| Feature | Description | Status | Priority |
|---|---|---|---|
| 6.1 Multi-region deployment | GCP regions for global low latency | To do | Low |
| 6.2 PII-free analytics | Anonymous usage analytics (PostHog or GA with IP masking) | To do | Medium |

---

## 7. Success Metrics (Anonymous Analytics)

No health data will be stored. Product learning comes from anonymous behavioral metrics:

| Metric | What it measures |
|---|---|
| Session funnel: start → export | Are the AI questions useful, or do users abandon? |
| Time on task | Complexity/quality of generated questions |
| Export format split (PDF / Copy / Print) | How patients prefer to carry info to the clinic |
| Optional end-of-session feedback (Yes/No) | Perceived usefulness — fully decoupled from health data |

---

## 8. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| LLM hallucination (AI attempts to diagnose) | High | Strict system prompts forbid diagnosis/treatment; output reviewed in prompt testing |
| API latency degrading UX | Medium | Optimize prompts for token efficiency; use streaming responses |
| Patient misuse as medical device | High | Persistent disclaimer on every screen and in every generated document |
| Privacy regression (data accidentally logged) | High | PII-free logging enforced in code; security regression test suite |

---

## 9. Roadmap

### Phase 2 — Completed (April 2026)
- Replaced RAG/ChromaDB with prompt engineering (OPQRST + SAMPLE)
- Migrated from Gradio to Reflex UI (React/Next.js)
- Integrated Redis for ephemeral session state (30-min TTL)
- Deployed to GCP Cloud Run with scale-to-zero
- Achieved 100% test coverage (unit, integration, security)
- Established GitHub Actions CI/CD pipeline
- (Since superseded) The Reflex frontend host was replaced by a plain Starlette app
  (`src/preconsult/host.py`) serving a standalone React + Vite SPA from `web/` at `/`

### Phase 3 — Current Backlog
Priority order based on architecture dependency and user impact:

**Blockers — must ship together (they form the new data pipeline):**
~~1. UX Step 3 — Structured medical history form (conditions, medications, allergies)~~
~~2. UX Step 4 — Lifestyle & family history form~~
~~3. Prompt 1 rework — Single LLM call receiving full form context (replaces OPQRST + SAMPLE chains)~~
~~4. Epic 3.1 — Deterministic PDF rework (`pdf_service.py` accepts form dict + Q&A array; removes LLM summarization)~~

**Fixes — features marked Done but not implemented:**
~~5. Epic 2.3 — Emergency detection rule in Prompt 1~~
~~6. Epic 3.3 — Copy to Clipboard button on export screen~~
~~7. Epic 3.4 — Auto-destruction notice copy in `complete_desc`~~

**UX polish — after blockers are resolved:**
~~8. Epic 4.1 — Progress bar / stepper already shipped → update status to Done~~
~~9. Epic 4.4 — Mobile touch targets (min 44px)~~
~~10. Epic 4.2 — Trust microcopy at each step~~
~~11. Epic 6.2 — PII-free analytics (enables product learning)~~
~~12. Epic 4.3 — Entrance animations (staggered sequence)~~
~~13. Epic 4.5 — Accessibility & contrast (WCAG)~~

**Future:**
14. Epic 5.1 — Specialized intake modes (Pediatric/Geriatric/Emergency)
15. Epic 5.2 — ICD-10 suggestions
16. Epic 6.1 — Multi-region deployment
