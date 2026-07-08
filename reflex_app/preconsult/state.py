import reflex as rx
import httpx
import json
import re
from typing import List, Dict, Any
import os
from datetime import datetime
from .i18n import translations
from .analytics import log_analytics_event, fetch_analytics_data

API_BASE_URL = os.environ.get("API_BASE_URL", "/api")
API_KEY = os.environ.get("PRECONSULT_API_KEY", "")

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
        return [{"id": k, "label": l} for k, l in zip(keys, labels)]

    @rx.var
    def conditions_opts_with_keys(self) -> List[Dict[str, str]]:
        keys = ["asthma", "depression", "diabetes", "hypertension", "thyroid"]
        labels = self._t["conditions_opts"]
        return [{"id": k, "label": l} for k, l in zip(keys, labels)]

    @rx.var
    def family_history_opts_with_keys(self) -> List[Dict[str, str]]:
        keys = ["alzheimers", "cancer", "diabetes", "heart"]
        labels = self._t["family_history_opts"]
        return [{"id": k, "label": l} for k, l in zip(keys, labels)]

    @rx.var
    def smoking_opts_with_keys(self) -> List[Dict[str, str]]:
        keys = ["never", "former", "current"]
        labels = self._t["smoking_opts"]
        return [{"id": k, "label": l} for k, l in zip(keys, labels)]

    @rx.var
    def alcohol_opts_with_keys(self) -> List[Dict[str, str]]:
        keys = ["never", "rarely", "socially", "frequently"]
        labels = self._t["alcohol_opts"]
        return [{"id": k, "label": l} for k, l in zip(keys, labels)]

    @rx.var
    def step_progress(self) -> int:
        return int(((self.step + 1) / 6) * 100)
    
    # --- General Form State ---
    gender: str = ""
    lang: str = "en"
    session_id: str = ""
    
    # --- Step 2: Chief Complaint ---
    specialist: str = ""
    age_bracket: str = "26-35"
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
    
    # --- UI State ---
    step: int = 0  # 0: Demographics, 1-4: Form, 5: Q&A, 6: Summary
    loading: bool = False

    def detect_lang(self):
        try:
            query_params = self.router.page.params
            lang_param = query_params.get("lang", "").lower()
            if lang_param in ["pt", "en"]:
                self.lang = lang_param
                return
            accept_lang = self.router.headers.get("accept-language", "")
            if "pt" in accept_lang.lower().split(",")[0]:
                self.lang = "pt"
            else:
                self.lang = "en"
        except Exception:
            self.lang = "en"

    def set_gender(self, val: str):
        self.gender = val

    def set_lang(self, val: str):
        self.lang = val

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

    def go_to_step_1(self):
        if not self.gender.strip():
            return rx.window_alert(self._t.get("err_gender", "Please select a biological sex."))
        self.step = 1
        self.log_analytics_event("demographics_submitted")

    def go_to_step_2(self):
        if not self.specialist.strip() or not self.chief_complaint.strip():
            return rx.window_alert(self._t["err_chief_complaint"])
        self.step = 2
        self.log_analytics_event("complaint_submitted")

    def go_to_step_3(self):
        self.step = 3
        self.log_analytics_event("history_submitted")

    def go_to_step_4(self):
        self.step = 4

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
                    f"{API_BASE_URL}/session/init",
                    json=payload,
                    headers={"X-API-KEY": API_KEY},
                    timeout=10.0
                )
                if resp.status_code == 200:
                    session_id = resp.json().get("session_id")
                    if not session_id:
                        yield rx.window_alert(self._t["err_generic"])
                        return
                    self.session_id = session_id
                    self.step = 4
                    self.log_analytics_event("lifestyle_submitted")
                    self.current_answers = []
                    self.questions = []
                    self.is_emergency = False
                    async for item in self.get_interview_questions():
                        yield item
                elif resp.status_code == 429:
                    yield rx.window_alert(self._t["err_rate_limit"])
                else:
                    yield rx.window_alert(self._t["err_init"])
            except Exception:
                yield rx.window_alert(self._t["err_generic"])
            finally:
                self.loading = False

    async def get_interview_questions(self):
        """Step 5 Streaming: Trigger interview questions."""
        self.loading = True
        self._qs_buffer = ""
        self.questions = []
        self.current_answers = []
        self.is_emergency = False
        yield
        
        async with httpx.AsyncClient() as client:
            try:
                headers = {"X-API-KEY": API_KEY}
                payload = {
                    "session_id": self.session_id
                }
                
                async with client.stream(
                    "POST", 
                    f"{API_BASE_URL}/interview-questions-stream", 
                    json=payload, 
                    headers=headers,
                    timeout=60.0
                ) as response:
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
                            self.questions = qs
                            
                            while len(self.current_answers) < len(self.questions):
                                self.current_answers.append("")
                            yield
            except Exception:
                yield rx.window_alert(self._t["err_stream"])
            finally:
                self.loading = False

    async def submit_answers(self):
        """Step 5 -> Step 6: Finalize."""
        if any(not ans.strip() for ans in self.current_answers[:len(self.questions)]):
            yield rx.window_alert(self._t.get("err_followup_ans", "Please answer all questions."))
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
        self.step = 5
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
                    f"{API_BASE_URL}/generate-pdf",
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
                    yield rx.window_alert(self._t["err_download"])
            except Exception:
                yield rx.window_alert(self._t["err_download_gen"])
            finally:
                self.loading = False


class AdminState(rx.State):
    token: str = ""
    authorized: bool = False
    analytics_data: List[Dict[str, Any]] = []
    
    async def load_analytics(self):
        query_params = self.router.page.params
        token_val = query_params.get("token", "")
        
        expected_token = os.environ.get("ADMIN_DASHBOARD_TOKEN", "preconsult_dev_token")
        if token_val == expected_token:
            self.authorized = True
            await self.fetch_analytics_data()
        else:
            self.authorized = False
            self.analytics_data = []

    async def fetch_analytics_data(self):
        self.analytics_data = await fetch_analytics_data()
