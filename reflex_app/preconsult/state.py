import reflex as rx
import httpx
import json
import re
from typing import List, Dict, Any
import os
from datetime import datetime
from .i18n import translations
from .analytics import log_analytics_event, fetch_analytics_data

API_KEY = os.environ.get("PRECONSULT_API_KEY", "")


def _api_url(path: str) -> str:
    base = os.environ.get("API_BASE_URL", "").rstrip("/")
    if base.startswith("http://") or base.startswith("https://"):
        return f"{base}/api{path}"
    return f"/api{path}"

class State(rx.State):
    """The app state."""

    @rx.var
    def t(self) -> dict:
        return translations.get(self.lang, translations["en"])

    @property
    def _t(self) -> dict:
        return translations.get(self.lang, translations["en"])

    @rx.var
    def gender_opts(self) -> List[str]:
        return self._t["gender_opts"]
        
    @rx.var
    def lang_opts(self) -> List[str]:
        return self._t["lang_opts"]

    @rx.var
    def step_names(self) -> List[str]:
        return self._t.get("step_names", [])

    @rx.var
    def duration_opts(self) -> List[str]:
        return self._t["duration_opts"]

    @rx.var
    def conditions_opts(self) -> List[str]:
        return self._t["conditions_opts"]

    @rx.var
    def family_history_opts(self) -> List[str]:
        return self._t["family_history_opts"]

    @rx.var
    def smoking_opts(self) -> List[str]:
        return self._t["smoking_opts"]

    @rx.var
    def alcohol_opts(self) -> List[str]:
        return self._t["alcohol_opts"]

    @rx.var
    def duration_opts_with_keys(self) -> List[Dict[str, str]]:
        keys = ["today", "days", "weeks", "months", "years"]
        labels = self._t["duration_opts"]
        return [{"id": k, "label": label} for k, label in zip(keys, labels)]

    @rx.var
    def conditions_opts_with_keys(self) -> List[Dict[str, str]]:
        keys = ["asthma", "depression", "diabetes", "hypertension", "thyroid"]
        labels = self._t["conditions_opts"]
        return [{"id": k, "label": label} for k, label in zip(keys, labels)]

    @rx.var
    def family_history_opts_with_keys(self) -> List[Dict[str, str]]:
        keys = ["alzheimers", "cancer", "diabetes", "heart"]
        labels = self._t["family_history_opts"]
        return [{"id": k, "label": label} for k, label in zip(keys, labels)]

    @rx.var
    def smoking_opts_with_keys(self) -> List[Dict[str, str]]:
        keys = ["never", "former", "current"]
        labels = self._t["smoking_opts"]
        return [{"id": k, "label": label} for k, label in zip(keys, labels)]

    @rx.var
    def alcohol_opts_with_keys(self) -> List[Dict[str, str]]:
        keys = ["never", "rarely", "socially", "frequently"]
        labels = self._t["alcohol_opts"]
        return [{"id": k, "label": label} for k, label in zip(keys, labels)]

    @rx.var
    def step_progress(self) -> int:
        return int(((self.step + 1) / 7) * 100)
    
    # --- General Form State ---
    gender: str = ""
    lang: str = "en"
    session_id: str = ""
    
    # --- Step 2: Chief Complaint ---
    specialist: str = ""
    age_bracket: str = ""
    chief_complaint: str = ""
    duration: str = ""
    complaint_detail: str = ""

    # --- Step 3: Medical History ---
    conditions: List[str] = []
    medications: List[str] = []
    allergies_flag: bool = False
    allergies_text: str = ""

    # --- Step 4: Lifestyle ---
    family_history: List[str] = []
    smoking: str = ""
    alcohol: str = ""

    # --- Conversation Content ---
    questions: List[str] = []
    current_answers: List[str] = []
    _qs_buffer: str = ""
    summary_text: str = ""
    is_emergency: bool = False
    question_index: int = 0
    
    # --- UI State ---
    step: int = 0  # 0: Landing, 1: Demographics, 2-5: Form, 6: Q&A, 7: Summary
    loading: bool = False
    error_message: str = ""

    def detect_lang(self):
        try:
            lang_cookie = self.get_cookie("preconsult_lang")
            if lang_cookie in ("pt", "en"):
                self.lang = lang_cookie
                return
            query_params = self.router.page.params
            lang_param = query_params.get("lang", "").lower()
            if lang_param in ("pt", "en"):
                self.lang = lang_param
                return
            accept_lang = self.router.headers.get("accept-language", "")
            parsed = []
            for entry in accept_lang.split(","):
                parts = entry.split(";")
                lang = parts[0].strip().lower().split("-")[0]
                q = 1.0
                if len(parts) > 1:
                    import re
                    m = re.search(r"q=([\d.]+)", parts[1])
                    if m:
                        q = float(m.group(1))
                if lang in ("en", "pt"):
                    parsed.append((lang, q))
            parsed.sort(key=lambda x: x[1], reverse=True)
            self.lang = parsed[0][0] if parsed else "en"
        except Exception:
            self.lang = "en"

    def set_gender(self, val: str):
        self.gender = val

    def set_lang(self, val: str):
        self.lang = val
        self.set_cookie("preconsult_lang", val, max_age=365 * 24 * 3600, path="/")

    def set_chief_complaint(self, val: str):
        self.chief_complaint = val

    def set_age_bracket(self, val: str):
        self.age_bracket = val

    def set_duration(self, val: str):
        self.duration = val

    def set_specialist(self, val: str):
        self.specialist = val

    def set_complaint_detail(self, val: str):
        self.complaint_detail = val

    def toggle_condition(self, condition: str):
        if condition in self.conditions:
            self.conditions.remove(condition)
        else:
            self.conditions.append(condition)

    def clear_conditions(self):
        self.conditions = []

    def toggle_family_history(self, item: str):
        if item in self.family_history:
            self.family_history.remove(item)
        else:
            self.family_history.append(item)

    def add_medication(self):
        meds = self.medications.copy()
        meds.append("")
        self.medications = meds

    def update_medication(self, idx: int, val: str):
        meds = self.medications.copy()
        meds[idx] = val
        self.medications = meds

    def remove_medication(self, idx: int):
        meds = self.medications.copy()
        meds.pop(idx)
        self.medications = meds

    def set_allergies_flag(self, val: bool):
        self.allergies_flag = val

    def set_allergies_text(self, val: str):
        self.allergies_text = val

    def set_smoking(self, val: str):
        self.smoking = val

    def set_alcohol(self, val: str):
        self.alcohol = val

    def set_answer(self, idx: int, val: str):
        answers = self.current_answers.copy()
        answers[idx] = val
        self.current_answers = answers

    def set_question_index(self, idx: int):
        self.question_index = idx

    def log_analytics_event(self, event_name: str):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(log_analytics_event(event_name))
        except RuntimeError:
            pass

    def get_localized_value(self, category: str, key: str) -> str:
        if not key:
            return ""
        keys_map = {
            "duration": ["today", "days", "weeks", "months", "years"],
            "conditions": ["asthma", "depression", "diabetes", "hypertension", "thyroid"],
            "family_history": ["alzheimers", "cancer", "diabetes", "heart"],
            "smoking": ["never", "former", "current"],
            "alcohol": ["never", "rarely", "socially", "frequently"]
        }
        opts_map = {
            "duration": "duration_opts",
            "conditions": "conditions_opts",
            "family_history": "family_history_opts",
            "smoking": "smoking_opts",
            "alcohol": "alcohol_opts"
        }
        if category not in keys_map:
            return key
        try:
            idx = keys_map[category].index(key)
            opts_list = self._t[opts_map[category]]
            if idx < len(opts_list):
                return opts_list[idx]
        except (ValueError, IndexError):
            pass
        return key

    def go_back(self):
        if self.step > 0:
            self.step -= 1
        self.error_message = ""

    def start_intake(self):
        self.error_message = ""
        self.step = 1
        self.log_analytics_event("intake_started")

    def go_to_step_2(self):
        if not self.gender.strip():
            self.error_message = self._t.get("err_gender", "Please select a biological sex.")
            return
        self.error_message = ""
        self.step = 2
        self.log_analytics_event("demographics_submitted")

    def go_to_step_3(self):
        if not self.specialist.strip() or not self.chief_complaint.strip():
            self.error_message = self._t["err_chief_complaint"]
            return
        self.error_message = ""
        self.step = 3
        self.log_analytics_event("complaint_submitted")

    def go_to_step_4(self):
        self.error_message = ""
        self.step = 4
        self.log_analytics_event("history_submitted")

    def go_to_step_5(self):
        self.step = 5

    async def init_session(self):
        """Step 4 -> Step 5: Initialize Redis session."""
        self.loading = True
        yield
        
        async with httpx.AsyncClient() as client:
            try:
                # payload conforming to Sprint 1
                payload = {
                    "age_bracket": self.age_bracket,
                    "sex": self.gender,
                    "lang": self.lang,
                    "specialist": self.specialist,
                    "chief_complaint": self.chief_complaint,
                    "duration": self.get_localized_value("duration", self.duration),
                    "complaint_detail": self.complaint_detail,
                    "conditions": [self.get_localized_value("conditions", c) for c in self.conditions],
                    "medications": [m for m in self.medications if m.strip()],
                    "allergies": self.allergies_text if self.allergies_flag else "None",
                    "family_history": [self.get_localized_value("family_history", f) for f in self.family_history],
                    "smoking": self.get_localized_value("smoking", self.smoking),
                    "alcohol": self.get_localized_value("alcohol", self.alcohol)
                }
                
                resp = await client.post(
                    _api_url("/session/init"),
                    json=payload,
                    headers={"X-API-KEY": API_KEY},
                    timeout=10.0
                )
                if resp.status_code == 200:
                    session_id = resp.json().get("session_id")
                    if not session_id:
                        self.error_message = self._t["err_generic"]
                        return
                    self.session_id = session_id
                    self.step = 5
                    self.error_message = ""
                    self.log_analytics_event("lifestyle_submitted")
                    self.current_answers = []
                    self.questions = []
                    self.question_index = 0
                    self.is_emergency = False
                    async for item in self.get_interview_questions():
                        yield item
                elif resp.status_code == 429:
                    self.error_message = self._t["err_rate_limit"]
                else:
                    self.error_message = self._t["err_init"]
            except Exception:
                self.error_message = self._t["err_generic"]
            finally:
                self.loading = False

    async def get_interview_questions(self):
        self.loading = True
        self._qs_buffer = ""
        self.questions = []
        self.current_answers = []
        self.question_index = 0
        self.is_emergency = False
        self.error_message = ""
        yield

        import asyncio
        stream_timeout = 30.0

        async with httpx.AsyncClient() as client:
            try:
                headers = {"X-API-KEY": API_KEY}
                payload = {
                    "session_id": self.session_id
                }
                
                async with asyncio.timeout(stream_timeout):
                    async with client.stream("POST", _api_url("/interview-questions-stream"), json=payload, headers=headers, timeout=stream_timeout + 5.0) as response:
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                chunk = json.loads(line[len("data: "):])
                            self._qs_buffer += chunk
                            
                            lower_buffer = self._qs_buffer.lower()
                            if "emergency" in lower_buffer or "911" in lower_buffer or "urgência" in lower_buffer or "urgencia" in lower_buffer:
                                self.is_emergency = True
                                self.questions = []
                                self.current_answers = []
                                yield
                                return
                                
                            # Match lines like "1. Question", "2) Question", etc. Very permissive match
                            qs = [q.strip() for q in re.split(r'\n(?:\d+[\.\)]|\-)\s*', '\n' + self._qs_buffer) if q.strip()]
                            # Fallback: if regex didn't split into multiple questions, split by any newline
                            if len(qs) <= 1:
                                qs = [q.strip() for q in self._qs_buffer.strip().split('\n') if q.strip()]
                            self.questions = qs
                            
                            while len(self.current_answers) < len(self.questions):
                                self.current_answers.append("")
                            yield
            except asyncio.TimeoutError:
                self.error_message = self._t["err_timeout"]
            except Exception:
                self.error_message = self._t["err_stream"]
            finally:
                self.loading = False

    async def submit_answers(self):
        if any(not ans.strip() for ans in self.current_answers[:len(self.questions)]):
            self.error_message = self._t.get("err_followup_ans", "Please answer all questions.")
            return
        
        # Build plain text summary for clipboard
        qs_ans_text = "\n\n".join(
            f"Q{i+1}: {q}\nA: {a}" 
            for i, (q, a) in enumerate(zip(self.questions, self.current_answers))
        )
        self.summary_text = (
            f"--- Patient Intake ---\n"
            f"Specialist: {self.specialist}\n"
            f"Chief Complaint: {self.chief_complaint}\n\n"
            f"--- Questions & Answers ---\n{qs_ans_text}"
        )
        self.step = 6
        self.log_analytics_event("summary_generated")

    async def download_report(self):
        """Step 6: Securely fetch PDF with API Key and trigger download."""
        self.loading = True
        yield
        
        async with httpx.AsyncClient() as client:
            try:
                headers = {"X-API-KEY": API_KEY}
                payload = {
                    "session_id": self.session_id,
                    "qa_pairs": [
                        {"question": q, "answer": a} 
                        for q, a in zip(self.questions, self.current_answers)
                    ]
                }
                resp = await client.post(
                    _api_url("/generate-pdf"),
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                if resp.status_code == 200:
                    self.log_analytics_event("pdf_downloaded")
                    yield rx.download(
                        data=resp.content,
                        filename=f"PreConsult_Report{datetime.now().strftime('_%y%m%d%H%M')}.pdf"
                    )
                else:
                    self.error_message = self._t["err_download"]
            except Exception:
                self.error_message = self._t["err_download_gen"]
            finally:
                self.loading = False


class AdminState(rx.State):
    token: str = ""
    authorized: bool = False
    analytics_data: List[Dict[str, Any]] = []
    
    async def load_analytics(self):
        query_params = self.router.page.params
        token_val = query_params.get("token", "")
        
        expected_token = os.environ.get("ADMIN_DASHBOARD_TOKEN")
        if expected_token and token_val == expected_token:
            self.authorized = True
            await self.fetch_analytics_data()
        else:
            self.authorized = False
            self.analytics_data = []

    async def fetch_analytics_data(self):
        self.analytics_data = await fetch_analytics_data()
