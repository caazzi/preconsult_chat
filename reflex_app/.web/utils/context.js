import { createContext, useContext, useMemo, useReducer, useState, createElement, useEffect } from "react"
import { applyDelta, ReflexEvent, hydrateClientStorage, useEventLoop, refs } from "$/utils/state"
import { jsx } from "@emotion/react";

export const initialState = {"reflex___state____state": {"is_hydrated_rx_state_": false, "router_rx_state_": {"session": {"client_token": "", "client_ip": "", "session_id": ""}, "headers": {"host": "", "origin": "", "upgrade": "", "connection": "", "cookie": "", "pragma": "", "cache_control": "", "user_agent": "", "sec_websocket_version": "", "sec_websocket_key": "", "sec_websocket_extensions": "", "accept_encoding": "", "accept_language": "", "raw_headers": {}}, "page": {"host": "", "path": "", "raw_path": "", "full_path": "", "full_raw_path": "", "params": {}}, "url": {"scheme": "", "netloc": "", "origin": "://", "path": "", "query": "", "query_parameters": {}, "fragment": "", "href": ""}, "route_id": ""}}, "reflex___state____state.preconsult___state____admin_state": {"analytics_data_rx_state_": [], "authorized_rx_state_": false, "token_rx_state_": ""}, "reflex___state____state.preconsult___state____state": {"active_step_index_rx_state_": 0, "active_step_name_rx_state_": "Patient Intake", "active_step_number_rx_state_": 1, "age_bracket_rx_state_": "", "alcohol_rx_state_": "", "alcohol_opts_rx_state_": ["Never", "Rarely", "Socially", "Frequently"], "alcohol_opts_with_keys_rx_state_": [{"id": "never", "label": "Never"}, {"id": "rarely", "label": "Rarely"}, {"id": "socially", "label": "Socially"}, {"id": "frequently", "label": "Frequently"}], "allergies_flag_rx_state_": false, "allergies_text_rx_state_": "", "chief_complaint_rx_state_": "", "complaint_detail_rx_state_": "", "conditions_rx_state_": [], "conditions_opts_rx_state_": ["Asthma/Bronchitis", "Depression/Anxiety", "Diabetes", "Hypertension", "Thyroid issues"], "conditions_opts_with_keys_rx_state_": [{"id": "asthma", "label": "Asthma/Bronchitis"}, {"id": "depression", "label": "Depression/Anxiety"}, {"id": "diabetes", "label": "Diabetes"}, {"id": "hypertension", "label": "Hypertension"}, {"id": "thyroid", "label": "Thyroid issues"}], "current_answers_rx_state_": [], "duration_rx_state_": "", "duration_opts_rx_state_": ["Started today", "A few days", "Weeks", "Months", "Years"], "duration_opts_with_keys_rx_state_": [{"id": "today", "label": "Started today"}, {"id": "days", "label": "A few days"}, {"id": "weeks", "label": "Weeks"}, {"id": "months", "label": "Months"}, {"id": "years", "label": "Years"}], "error_message_rx_state_": "", "family_history_rx_state_": [], "family_history_opts_rx_state_": ["Alzheimer's", "Cancer", "Diabetes", "Heart disease/Heart attack"], "family_history_opts_with_keys_rx_state_": [{"id": "alzheimers", "label": "Alzheimer's"}, {"id": "cancer", "label": "Cancer"}, {"id": "diabetes", "label": "Diabetes"}, {"id": "heart", "label": "Heart disease/Heart attack"}], "gad_campaignid_rx_state_": "", "gad_source_rx_state_": "", "gbraid_rx_state_": "", "gclid_rx_state_": "", "gender_rx_state_": "", "gender_opts_rx_state_": ["Prefer not to say", "Female", "Male", "Intersex"], "is_emergency_rx_state_": false, "lang_rx_state_": "en", "lang_opts_rx_state_": ["en", "pt"], "loading_rx_state_": false, "medications_rx_state_": [], "question_index_rx_state_": 0, "questions_rx_state_": [], "session_id_rx_state_": "", "smoking_rx_state_": "", "smoking_opts_rx_state_": ["Never smoked", "Former smoker", "Currently smoke"], "smoking_opts_with_keys_rx_state_": [{"id": "never", "label": "Never smoked"}, {"id": "former", "label": "Former smoker"}, {"id": "current", "label": "Currently smoke"}], "specialist_rx_state_": "", "step_rx_state_": 0, "step_names_rx_state_": ["Patient Intake", "Chief Complaint", "Medical History", "Lifestyle & Family", "Clinical Assessment"], "step_progress_rx_state_": 0, "summary_text_rx_state_": "", "t_rx_state_": {"title": "PreConsult", "intake": "Patient Intake", "intake_desc": "Tell us about yourself. We'll help you organize your thoughts.", "age": "Age Bracket", "age_ph": "Ex: 26-35", "gender": "Biological Sex", "gender_opts": ["Prefer not to say", "Female", "Male", "Intersex"], "gender_ph": "Select Sex at Birth", "lang": "Language Preference", "lang_opts": ["en", "pt"], "lang_ph": "Select Language", "start_cta": "Start Preparing", "start_btn": "Continue", "back_btn": "Back", "hero_title": "Prepare for your doctor's appointment in 3 minutes", "hero_subtitle": "Organize your symptoms into a structured medical report for your doctor.", "step_how_1": "Tell your symptoms", "step_how_2": "AI asks questions", "step_how_3": "Download the PDF", "step_sub_1": "Describe what you're feeling.", "step_sub_2": "Answer a few clinical questions.", "step_sub_3": "A report ready for your doctor.", "privacy_badge": "🔒 Zero Data Persistence: No account needed. Your data is deleted upon closing.", "privacy_badge_landing": "🔒 No sign-up. Your data is deleted when you close.", "privacy_step_note": "🔒 Your answers are temporary and private", "step_1": "Chief Complaint", "step_1_desc": "What brought you to book this appointment?", "specialist": "Specialist you are seeing", "specialist_ph": "Ex: Gastroenterologist", "concern": "Chief Complaint", "concern_ph": "Describe your main problem. What makes it better or worse?", "duration": "Duration (How long has this been happening?)", "duration_opts": ["Started today", "A few days", "Weeks", "Months", "Years"], "step_2": "Medical History", "step_2_desc": "Information about your past health.", "conditions_label": "Pre-existing conditions", "conditions_opts": ["Asthma/Bronchitis", "Depression/Anxiety", "Diabetes", "Hypertension", "Thyroid issues"], "conditions_none": "None of the above", "other_label": "Other (please specify)", "medications_label": "Current medications", "medications_ph": "Ex: Losartan 50mg", "add_medication": "+ Add medication", "remove": "Remove", "allergies_label": "Do you have any drug allergies?", "allergies_yes": "Yes", "allergies_no": "No", "allergies_ph": "List your drug allergies...", "step_3": "Lifestyle & Family", "step_3_desc": "These details help your doctor understand your full context.", "family_history_label": "Family History (Parents or Siblings)", "family_history_opts": ["Alzheimer's", "Cancer", "Diabetes", "Heart disease/Heart attack"], "smoking_label": "Smoking status", "smoking_opts": ["Never smoked", "Former smoker", "Currently smoke"], "alcohol_label": "Alcohol consumption", "alcohol_opts": ["Never", "Rarely", "Socially", "Frequently"], "generate_qs_btn": "Generate My Questions", "emergency_title": "EMERGENCY WARNING", "emergency_body": "If you are experiencing a medical emergency, please call 911 (US) or your local emergency number immediately.\n\nThis tool is not a substitute for professional medical help.", "emergency_cta": "I understand, go to start", "step_4": "Clinical Assessment", "step_4_desc": "A few more questions to give your doctor the full picture.", "opqrst": "Clinical Questions", "question_counter": "Question {current} of {total}", "answers_ph": "Type your answer here...", "submit_continue": "Generate My Summary", "step_5": "Summary", "step_5_desc": "Your summary is ready. Once you close this window, all data is permanently deleted from our servers.", "complete_title": "Report Ready", "complete_desc": "Your summary is ready. Once you close this window, all data is permanently deleted from our servers.", "download_btn": "Download PDF Report", "copy_btn": "Copy to Clipboard", "print_btn": "Print Report", "copy_success": "Copied to clipboard!", "start_new": "Start New Session", "step_names": ["Patient Intake", "Chief Complaint", "Medical History", "Lifestyle & Family", "Clinical Assessment"], "step_indicator": "Step", "of_indicator": "of", "err_gender": "Please select a biological sex.", "err_chief_complaint": "Please enter a chief complaint.", "err_init": "Failed to init session. Please try again.", "err_generic": "An unexpected error occurred. Please try again.", "err_stream": "Failed to load questions. Please try again.", "err_timeout": "The request timed out. Please try again.", "err_rate_limit": "Too many requests. Please wait a moment.", "err_initial_ans": "Please answer the questions.", "err_followup_ans": "Please answer all questions.", "err_download": "Failed to download PDF. Please try again.", "err_download_gen": "An unexpected error occurred during download.", "lang_select_sr": "Select language", "gender_select_sr": "Select your gender", "footer_disclaimer": "PreConsult helps you prepare for medical appointments. It does not provide medical diagnosis, treatment, or emergency services. Always consult a qualified healthcare professional for medical advice. If you are experiencing a medical emergency, call your local emergency number immediately.", "footer_privacy": "Privacy Policy", "footer_terms": "Terms of Service", "faq_title": "Frequently Asked Questions", "faq_q1": "What is PreConsult?", "faq_a1": "PreConsult is a privacy-first tool that helps you organize your symptoms and medical history into a structured PDF report before your doctor's appointment. It uses AI to ask relevant clinical questions based on what you share.", "faq_q2": "Is my data stored or shared?", "faq_a2": "No. All data is processed temporarily and permanently deleted when you close the browser tab. No account or sign-up is required. We do not sell or share your information.", "faq_q3": "Do I need to create an account?", "faq_a3": "No. PreConsult is completely anonymous. Just open the page and start.", "faq_q4": "Is this a replacement for medical advice?", "faq_a4": "No. PreConsult is an organizational tool to help you prepare for appointments. It does not provide diagnosis, treatment recommendations, or medical advice. Always consult a qualified healthcare professional.", "faq_q5": "Who is this for?", "faq_a5": "Anyone with an upcoming doctor's appointment who wants to arrive better prepared. It's useful for specialists, general practitioners, and check-ups.", "privacy_title": "Privacy Policy", "privacy_text": "PreConsult is committed to protecting your privacy. We do not store, sell, or share any personal health information you enter. All data is processed temporarily in memory and permanently deleted when you close the browser tab. No account creation, cookies for tracking, or persistent identifiers are used. We use Anthropic's Claude (Haiku) hosted on AWS Bedrock to generate clinical questions based on the information you provide, but no conversation data is retained after your session ends.", "terms_title": "Terms of Service", "terms_text": "By using PreConsult, you agree that this tool is for informational and organizational purposes only. It does not provide medical diagnosis, treatment recommendations, or emergency services. You should always consult a qualified healthcare professional for medical advice. If you are experiencing a medical emergency, call your local emergency number immediately. PreConsult is provided \"as is\" without warranties of any kind. The developers are not liable for any damages arising from the use of this tool."}, "total_active_steps_rx_state_": 5, "utm_campaign_rx_state_": "", "utm_source_rx_state_": ""}, "reflex___state____state.reflex___istate___shared____shared_state_base_internal": {}, "reflex___state____state.reflex___state____frontend_event_exception_state": {}, "reflex___state____state.reflex___state____on_load_internal_state": {}, "reflex___state____state.reflex___state____update_vars_internal_state": {}}

export const defaultColorMode = "dark"
export const ColorModeContext = createContext({
  colorMode: defaultColorMode,
  resolvedColorMode: defaultColorMode === "dark" ? "dark" : "light",
  toggleColorMode: () => {},
  setColorMode: () => {},
});
export const UploadFilesContext = createContext(null);
export const DispatchContext = createContext(null);
export const StateContexts = {reflex___state____state: createContext(null),reflex___state____state__preconsult___state____admin_state: createContext(null),reflex___state____state__preconsult___state____state: createContext(null),reflex___state____state__reflex___istate___shared____shared_state_base_internal: createContext(null),reflex___state____state__reflex___state____frontend_event_exception_state: createContext(null),reflex___state____state__reflex___state____on_load_internal_state: createContext(null),reflex___state____state__reflex___state____update_vars_internal_state: createContext(null),};
export const EventLoopContext = createContext(null);
export const clientStorage = {"cookies": {"reflex___state____state.preconsult___state____state.lang_rx_state_": {"name": "preconsult_lang", "path": "/", "maxAge": 31536000, "sameSite": "lax"}}, "local_storage": {}, "session_storage": {}}


export const state_name = "reflex___state____state"

export const exception_state_name = "reflex___state____state.reflex___state____frontend_event_exception_state"

// These events are triggered on initial load and each page navigation.
export const onLoadInternalEvent = () => {
    const internal_events = [];

    // Get tracked cookie and local storage vars to send to the backend.
    const client_storage_vars = hydrateClientStorage(clientStorage);
    // But only send the vars if any are actually set in the browser.
    if (client_storage_vars && Object.keys(client_storage_vars).length !== 0) {
        internal_events.push(
            ReflexEvent(
                'reflex___state____state.reflex___state____update_vars_internal_state.update_vars_internal',
                {vars: client_storage_vars},
            ),
        );
    }

    // `on_load_internal` triggers the correct on_load event(s) for the current page.
    // If the page does not define any on_load event, this will just set `is_hydrated = true`.
    internal_events.push(ReflexEvent('reflex___state____state.reflex___state____on_load_internal_state.on_load_internal'));

    return internal_events;
}

// The following events are sent when the websocket connects or reconnects.
export const initialEvents = () => [
    ReflexEvent('reflex___state____state.hydrate'),
    ...onLoadInternalEvent()
]
    

export const isDevMode = false;

// Module-level event dispatchers populated by ``EventLoopProvider`` on each
// render. Components reach addEvents/connectErrors via this import instead of
// hoisting ``useContext(EventLoopContext)`` so JSX literals (e.g.
// ``ErrorBoundary.onError``) constructed in any JS scope can dispatch events
// without depending on lexical hook hoisting.
let _addEventsImpl = (events, args, event_actions) => {
  console.warn("addEvents called before EventLoopProvider mounted", events);
};
let _connectErrorsImpl = [];

export function addEvents(events, args, event_actions) {
  return _addEventsImpl(events, args, event_actions);
}

export function getConnectErrors() {
  return _connectErrorsImpl;
}

export function UploadFilesProvider({ children }) {
  const [filesById, setFilesById] = useState({})
  refs["__clear_selected_files"] = (id) => setFilesById(filesById => {
    const newFilesById = {...filesById}
    delete newFilesById[id]
    return newFilesById
  })
  return createElement(
    UploadFilesContext.Provider,
    { value: [filesById, setFilesById] },
    children
  );
}

export function ClientSide(component) {
  return ({ children, ...props }) => {
    const [Component, setComponent] = useState(null);
    useEffect(() => {
      async function load() {
        const comp = await component();
        setComponent(() => comp);
      }
      load();
    }, []);
    return Component ? jsx(Component, props, children) : null;
  };
}

export function EventLoopProvider({ children }) {
  const dispatch = useContext(DispatchContext)
  const [addEventsLocal, connectErrors] = useEventLoop(
    dispatch,
    initialEvents,
    clientStorage,
  )
  // Populate the module-level dispatchers so JSX literals constructed
  // outside the React-tree path (e.g. ``ErrorBoundary.onError``) can call
  // ``addEvents`` without needing the events hook hoisted in their scope.
  _addEventsImpl = addEventsLocal;
  _connectErrorsImpl = connectErrors;
  return createElement(
    EventLoopContext.Provider,
    { value: [addEventsLocal, connectErrors] },
    children
  );
}

export function StateProvider({ children }) {
  const [reflex___state____state, dispatch_reflex___state____state] = useReducer(applyDelta, initialState["reflex___state____state"])
const [reflex___state____state__preconsult___state____admin_state, dispatch_reflex___state____state__preconsult___state____admin_state] = useReducer(applyDelta, initialState["reflex___state____state.preconsult___state____admin_state"])
const [reflex___state____state__preconsult___state____state, dispatch_reflex___state____state__preconsult___state____state] = useReducer(applyDelta, initialState["reflex___state____state.preconsult___state____state"])
const [reflex___state____state__reflex___istate___shared____shared_state_base_internal, dispatch_reflex___state____state__reflex___istate___shared____shared_state_base_internal] = useReducer(applyDelta, initialState["reflex___state____state.reflex___istate___shared____shared_state_base_internal"])
const [reflex___state____state__reflex___state____frontend_event_exception_state, dispatch_reflex___state____state__reflex___state____frontend_event_exception_state] = useReducer(applyDelta, initialState["reflex___state____state.reflex___state____frontend_event_exception_state"])
const [reflex___state____state__reflex___state____on_load_internal_state, dispatch_reflex___state____state__reflex___state____on_load_internal_state] = useReducer(applyDelta, initialState["reflex___state____state.reflex___state____on_load_internal_state"])
const [reflex___state____state__reflex___state____update_vars_internal_state, dispatch_reflex___state____state__reflex___state____update_vars_internal_state] = useReducer(applyDelta, initialState["reflex___state____state.reflex___state____update_vars_internal_state"])
  const dispatchers = useMemo(() => {
    return {
      "reflex___state____state": dispatch_reflex___state____state,
"reflex___state____state.preconsult___state____admin_state": dispatch_reflex___state____state__preconsult___state____admin_state,
"reflex___state____state.preconsult___state____state": dispatch_reflex___state____state__preconsult___state____state,
"reflex___state____state.reflex___istate___shared____shared_state_base_internal": dispatch_reflex___state____state__reflex___istate___shared____shared_state_base_internal,
"reflex___state____state.reflex___state____frontend_event_exception_state": dispatch_reflex___state____state__reflex___state____frontend_event_exception_state,
"reflex___state____state.reflex___state____on_load_internal_state": dispatch_reflex___state____state__reflex___state____on_load_internal_state,
"reflex___state____state.reflex___state____update_vars_internal_state": dispatch_reflex___state____state__reflex___state____update_vars_internal_state,
    }
  }, [])

  return (
    createElement(StateContexts.reflex___state____state,{value: reflex___state____state},
createElement(StateContexts.reflex___state____state__preconsult___state____admin_state,{value: reflex___state____state__preconsult___state____admin_state},
createElement(StateContexts.reflex___state____state__preconsult___state____state,{value: reflex___state____state__preconsult___state____state},
createElement(StateContexts.reflex___state____state__reflex___istate___shared____shared_state_base_internal,{value: reflex___state____state__reflex___istate___shared____shared_state_base_internal},
createElement(StateContexts.reflex___state____state__reflex___state____frontend_event_exception_state,{value: reflex___state____state__reflex___state____frontend_event_exception_state},
createElement(StateContexts.reflex___state____state__reflex___state____on_load_internal_state,{value: reflex___state____state__reflex___state____on_load_internal_state},
createElement(StateContexts.reflex___state____state__reflex___state____update_vars_internal_state,{value: reflex___state____state__reflex___state____update_vars_internal_state},
    createElement(DispatchContext, {value: dispatchers}, children)
    )))))))
  )
}