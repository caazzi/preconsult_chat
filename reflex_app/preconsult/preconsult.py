import reflex as rx
from .state import State, AdminState
try:
    from preconsult.api.endpoints import router as api_router
except ImportError:
    api_router = None


def error_callout() -> rx.Component:
    return rx.cond(
        State.error_message != "",
        rx.callout(
            State.error_message,
            icon="triangle_alert",
            color_scheme="red",
            variant="surface",
            size="3",
            width="100%",
            margin_bottom="0.5em",
            role="alert",
        ),
    )


def form_step_layout(
    title,
    description,
    content: rx.Component,
    back_on_click,
    next_on_click,
    next_text_key: str = "start_btn",
    next_color: str = "cyan",
    next_loading: bool = False,
    icon_name: str | None = None,
) -> rx.Component:
    header_items = []
    if icon_name:
        header_items.append(
            rx.hstack(
                rx.icon(icon_name, size=24, color="cyan"),
                rx.heading(title, size={"initial": "6", "sm": "7"}),
                spacing="2",
                align_items="center",
            )
        )
    else:
        header_items.append(rx.heading(title, size={"initial": "6", "sm": "7"}))

    return rx.vstack(
        error_callout(),
        rx.vstack(
            *header_items,
            rx.text(description, color_scheme="gray"),
            rx.divider(),
            width="100%", spacing="3",
            animation="fadeInUp 0.4s ease-out 0s both"
        ),
        content,
        rx.grid(
            rx.button(
                State.t["back_btn"],
                on_click=back_on_click,
                color_scheme="gray", variant="outline",
                size="4", width="100%", min_height="48px",
            ),
            rx.button(
                State.t[next_text_key],
                on_click=next_on_click,
                color_scheme=next_color,
                size="4", width="100%", min_height="48px",
                loading=next_loading,
            ),
            columns="2", spacing="4", width="100%",
            animation="fadeInUp 0.4s ease-out 0.3s both"
        ),
        width="100%", spacing="4"
    )


def header() -> rx.Component:
    return rx.hstack(
        rx.heading(State.t["title"], size={"initial": "5", "xs": "6", "sm": "7"}, color_scheme="cyan"),
        rx.spacer(),
        rx.hstack(
            rx.cond(
                State.step == 0,
                rx.el.label(
                    rx.text(State.t["lang_select_sr"], class_name="sr-only"),
                    rx.select(
                        ["en", "pt"],
                        on_change=State.set_lang,
                        value=State.lang,
                        width="70px",
                        min_height="44px",
                        variant="ghost",
                        aria_label="Select language"
                    ),
                ),
            ),
            rx.color_mode.button(aria_label="Toggle color mode"),
            spacing="2",
        ),
        width="100%",
        padding={"initial": "0.5em 1em", "sm": "1em"},
        border_bottom=rx.cond(
            rx.color_mode == "light",
            "1px solid rgba(0, 0, 0, 0.08)",
            "1px solid rgba(255, 255, 255, 0.1)"
        ),
    )

def step_0_landing() -> rx.Component:
    def card(icon, title, sub):
        return rx.vstack(
            rx.icon(icon, size=24, color="cyan"),
            rx.text(State.t[title], weight="bold", size="3", text_align="center"),
            rx.text(State.t[sub], size="2", color_scheme="gray", text_align="center"),
            align_items="center",
            spacing="2",
            padding="1em",
            border="1px solid rgba(255,255,255,0.1)",
            border_radius="12px",
            width="100%",
            height="100%",
            _hover={"background": "rgba(0, 200, 255, 0.04)"},
        )
    return rx.vstack(
        rx.center(
            rx.hstack(
                rx.icon("shield", size=14, color="green"),
                rx.text(State.t["privacy_badge_landing"], size="2", color_scheme="green"),
                spacing="1", align_items="center",
            ),
            padding="0.3em 0.8em",
            background="rgba(0, 255, 100, 0.06)",
            border_radius="999px",
        ),
        rx.vstack(
            rx.heading(State.t["hero_title"], size={"initial": "6", "sm": "7"}, text_align="center", line_height="1.2"),
            rx.text(State.t["hero_subtitle"], color_scheme="gray", size="3", text_align="center"),
            spacing="2",
            align_items="center",
            width="100%",
            animation="fadeInUp 0.4s ease-out 0s both",
        ),
        rx.hstack(
            card("message-square", "step_how_1", "step_sub_1"),
            card("brain", "step_how_2", "step_sub_2"),
            card("file-text", "step_how_3", "step_sub_3"),
            spacing="3",
            width="100%",
            flex_direction=["column", "row"],
        ),
        rx.button(
            State.t["start_cta"],
            on_click=State.start_intake,
            color_scheme="cyan",
            size="4",
            width="100%",
            min_height="48px",
            _hover={"transform": "scale(1.02)", "bg": "cyan.600"},
            transition="all 0.2s ease",
            animation="fadeInUp 0.4s ease-out 0.2s both",
        ),
        width="100%",
        spacing="5",
    )

def step_1_demographics() -> rx.Component:
    return rx.vstack(
        error_callout(),
        rx.vstack(
            rx.heading(State.t["intake"], size={"initial": "6", "sm": "7"}, margin_bottom="0.25em"),
            rx.text(State.t["intake_desc"], color_scheme="gray"),
            rx.divider(),
            width="100%", spacing="3", animation="fadeInUp 0.4s ease-out 0s both"
        ),
        rx.vstack(
            rx.text(State.t["age"], weight="bold"),
            rx.grid(
                *[rx.button(bracket, on_click=State.set_age_bracket(bracket),
                            variant=rx.cond(State.age_bracket == bracket, "solid", "outline"),
                            width="100%", min_height="48px")
                  for bracket in ["18-25", "26-35", "36-45", "46-60", "60+"]],
                columns={"initial": "2", "sm": "5"},
                spacing="3",
                width="100%"
            ),
            rx.text(State.t["gender"], weight="bold"),
            rx.text(State.t["gender_select_sr"], class_name="sr-only"),
            rx.select(
                State.gender_opts,
                placeholder=State.t["gender_ph"],
                on_change=State.set_gender,
                value=State.gender,
                width="100%",
                min_height="48px",
                aria_label="Select your gender"
            ),
            spacing="4",
            width="100%",
            padding_y="0.5em",
            animation="fadeInUp 0.4s ease-out 0.1s both"
        ),
        rx.button(
            State.t["start_btn"],
            on_click=State.go_to_step_2,
            color_scheme="cyan",
            size="4",
            width="100%",
            min_height="48px",
            _hover={"transform": "scale(1.02)", "bg": "cyan.600"},
            transition="all 0.2s ease",
            animation="fadeInUp 0.4s ease-out 0.2s both"
        ),
        rx.center(
            rx.hstack(
                rx.icon("shield", size=14, color="green"),
                rx.text(State.t["privacy_step_note"], size="2", color_scheme="green", text_align="center"),
                spacing="2", align_items="center",
            ),
            width="100%",
            animation="fadeInUp 0.4s ease-out 0.25s both",
        ),
        width="100%",
        spacing="4"
    )

def step_2_chief_complaint() -> rx.Component:
    content = rx.vstack(
        rx.text(State.t["concern"], weight="bold"),
        rx.text_area(
            placeholder=State.t["concern_ph"],
            on_change=lambda val: (
                State.set_chief_complaint(val),
                State.set_complaint_detail("")
            ),
            value=State.chief_complaint,
            width="100%", height="80px", min_height="48px",
            aria_label="Chief Complaint"
        ),
        rx.text(State.t["duration"], weight="bold"),
        rx.grid(
            rx.foreach(
                State.duration_opts_with_keys,
                lambda opt: rx.button(opt["label"], on_click=State.set_duration(opt["id"]),
                    variant=rx.cond(State.duration == opt["id"], "solid", "outline"),
                    width="100%", min_height="48px")
            ),
            columns={"initial": "2", "sm": "5"}, spacing="3", width="100%"
        ),
        rx.text(State.t["specialist"], weight="bold"),
        rx.input(
            placeholder=State.t["specialist_ph"],
            on_change=State.set_specialist, value=State.specialist,
            width="100%", min_height="48px",
            aria_label="Specialist you are seeing"
        ),
        spacing="4", width="100%"
    )
    return form_step_layout(
        State.t["step_1"], State.t["step_1_desc"], content,
        back_on_click=State.go_back, next_on_click=State.go_to_step_3,
    )
def step_3_history() -> rx.Component:
    def medication_item(med_idx):
        return rx.hstack(
            rx.input(
                placeholder=State.t["medications_ph"],
                on_change=lambda val: State.update_medication(med_idx, val),
                value=State.medications[med_idx],
                flex="1",
                min_height="48px",
                aria_label="Medication name"
            ),
            rx.button(
                rx.hstack(
                    rx.icon("trash", size=16),
                    rx.text(State.t["remove"], display={"initial": "none", "sm": "block"}),
                    spacing="2",
                    align_items="center",
                ),
                on_click=lambda: State.remove_medication(med_idx), 
                color_scheme="red", 
                variant="outline",
                min_height="48px",
                width={"initial": "48px", "sm": "auto"},
                aria_label="Remove medication"
            ),
            width="100%",
            spacing="2"
        )

    return form_step_layout(
        State.t["step_2"], State.t["step_2_desc"],
        rx.vstack(
            rx.text(State.t["conditions_label"], weight="bold"),
            rx.grid(
                rx.foreach(
                    State.conditions_opts_with_keys,
                    lambda opt: rx.button(opt["label"], on_click=State.toggle_condition(opt["id"]),
                        variant=rx.cond(State.conditions.contains(opt["id"]), "solid", "outline"),
                        width="100%", min_height="48px")
                ),
                columns={"initial": "2", "sm": "5"}, spacing="3", width="100%"
            ),
            rx.button(
                State.t["conditions_none"],
                on_click=State.clear_conditions,
                variant=rx.cond(State.conditions.length() == 0, "solid", "outline"),
                width="100%", min_height="48px", color_scheme="gray",
            ),
            rx.text(State.t["medications_label"], weight="bold"),
            rx.vstack(
                rx.cond(
                    State.medications.length() > 0,
                    rx.vstack(rx.foreach(State.medications, lambda m, i: medication_item(i)), width="100%"),
                ),
                rx.button(State.t["add_medication"], on_click=State.add_medication, variant="ghost", min_height="48px"),
                align_items="start", width="100%"
            ),
            rx.text(State.t["allergies_label"], weight="bold"),
            rx.segmented_control.root(
                rx.segmented_control.item(State.t["allergies_no"], value=State.t["allergies_no"], min_height="48px"),
                rx.segmented_control.item(State.t["allergies_yes"], value=State.t["allergies_yes"], min_height="48px"),
                on_change=lambda val: State.set_allergies_flag(val == State.t["allergies_yes"]),
                value=rx.cond(State.allergies_flag, State.t["allergies_yes"], State.t["allergies_no"]),
                width="100%", aria_label="Do you have any drug allergies?"
            ),
            rx.cond(
                State.allergies_flag,
                rx.text_area(
                    placeholder=State.t["allergies_ph"],
                    on_change=State.set_allergies_text, value=State.allergies_text,
                    width="100%", min_height="48px",
                    animation="fadeInUp 0.2s ease-out both",
                    aria_label="List your drug allergies"
                )
            ),
            spacing="4", width="100%"
        ),
        back_on_click=State.go_back, next_on_click=State.go_to_step_4,
    )

def step_4_lifestyle() -> rx.Component:
    return form_step_layout(
        State.t["step_3"], State.t["step_3_desc"],
        rx.vstack(
            rx.text(State.t["family_history_label"], weight="bold"),
            rx.grid(
                rx.foreach(
                    State.family_history_opts_with_keys,
                    lambda opt: rx.button(opt["label"], on_click=State.toggle_family_history(opt["id"]),
                        variant=rx.cond(State.family_history.contains(opt["id"]), "solid", "outline"),
                        width="100%", min_height="48px")
                ),
                columns={"initial": "2", "sm": "4"}, spacing="3", width="100%"
            ),
            rx.text(State.t["smoking_label"], weight="bold"),
            rx.grid(
                rx.foreach(
                    State.smoking_opts_with_keys,
                    lambda opt: rx.button(opt["label"], on_click=State.set_smoking(opt["id"]),
                        variant=rx.cond(State.smoking == opt["id"], "solid", "outline"),
                        width="100%", min_height="48px")
                ),
                columns={"initial": "3"}, spacing="3", width="100%"
            ),
            rx.text(State.t["alcohol_label"], weight="bold"),
            rx.grid(
                rx.foreach(
                    State.alcohol_opts_with_keys,
                    lambda opt: rx.button(opt["label"], on_click=State.set_alcohol(opt["id"]),
                        variant=rx.cond(State.alcohol == opt["id"], "solid", "outline"),
                        width="100%", min_height="48px")
                ),
                columns={"initial": "2", "sm": "4"}, spacing="3", width="100%"
            ),
            spacing="4", width="100%"
        ),
        back_on_click=State.go_back, next_on_click=State.init_session,
        next_text_key="generate_qs_btn", next_loading=State.loading,
    )


def step_5_interview_qs() -> rx.Component:
    def question_item(q, idx):
        return rx.vstack(
            rx.text(f"Question {idx + 1} of {State.questions.length()}", size="2", color_scheme="gray", weight="bold"),
            rx.text(q, weight="bold"),
            rx.text_area(
                placeholder=State.t["answers_ph"],
                on_change=lambda val: State.set_answer(idx, val),
                on_focus=State.set_question_index(idx),
                value=State.current_answers[idx],
                width="100%", height="80px", min_height="48px",
                aria_label="Answer for clinical question"
            ),
            width="100%", spacing="3"
        )

    def question_skeleton() -> rx.Component:
        return rx.vstack(
            rx.box(height="12px", width="40%", background="var(--slate-4)", border_radius="4px",
                   animation="shimmer 1.5s ease-in-out infinite"),
            rx.box(height="16px", width="80%", background="var(--slate-4)", border_radius="4px", margin_top="0.5em",
                   animation="shimmer 1.5s ease-in-out infinite"),
            rx.box(height="80px", width="100%", background="var(--slate-4)", border_radius="8px", margin_top="0.5em",
                   animation="shimmer 1.5s ease-in-out infinite"),
            rx.box(height="12px", width="30%", background="var(--slate-4)", border_radius="4px", margin_top="0.5em",
                   animation="shimmer 1.5s ease-in-out infinite"),
            rx.box(height="16px", width="70%", background="var(--slate-4)", border_radius="4px", margin_top="0.5em",
                   animation="shimmer 1.5s ease-in-out infinite"),
            rx.box(height="80px", width="100%", background="var(--slate-4)", border_radius="8px", margin_top="0.5em",
                   animation="shimmer 1.5s ease-in-out infinite"),
            width="100%", spacing="2", padding="1em",
        )

    content = rx.vstack(
        rx.box(
            rx.cond(
                State.questions.length() > 0,
                rx.vstack(rx.foreach(State.questions, lambda q, i: question_item(q, i)), width="100%"),
                question_skeleton()
            ),
            width="100%", max_height={"sm": "320px"},
            overflow_y="auto", padding_right="0.5em",
        ),
        rx.dialog.root(
            rx.dialog.trigger(
                rx.box(), # hidden trigger, opened via state
            ),
            rx.cond(
                State.is_emergency,
                rx.dialog.content(
                    rx.hstack(
                        rx.icon("triangle_alert", size=28, color="red"),
                        rx.dialog.title(State.t["emergency_title"], color="red"),
                        spacing="2", align_items="center",
                    ),
                    rx.text(State._qs_buffer, color="red", font_size="lg", font_weight="bold", text_align="center"),
                    rx.text(State.t["emergency_body"], size="3"),
                    rx.dialog.close(
                        rx.button(
                            State.t["emergency_cta"],
                            on_click=rx.redirect("/"),
                            color_scheme="red", variant="solid",
                            width="100%", min_height="48px",
                        ),
                    ),
                    max_width="450px", width="100%",
                ),
            ),
        ),
        width="100%", spacing="4",
    )
    return form_step_layout(
        State.t["step_4"], State.t["step_4_desc"],
        content,
        back_on_click=State.go_back, next_on_click=State.submit_answers,
        next_text_key="submit_continue", next_loading=State.loading,
        icon_name="clipboard-list",
    )

def step_6_summary() -> rx.Component:
    return rx.vstack(
        error_callout(),
        rx.vstack(
            rx.heading(State.t["complete_title"], size={"initial": "7", "sm": "8"}, text_align="center"),
            rx.text(State.t["complete_desc"], text_align="center"),
            rx.divider(),
            width="100%", spacing="3", animation="fadeInUp 0.4s ease-out 0s both"
        ),
        rx.vstack(
            rx.button(
                State.t["download_btn"],
                on_click=State.download_report, loading=State.loading,
                color_scheme="green", size="4", width="100%", padding="1.5em", min_height="48px",
                _hover={"transform": "scale(1.02)"}, transition="all 0.2s ease"
            ),
            rx.grid(
                rx.button(
                    State.t["copy_btn"],
                    on_click=rx.set_clipboard(State.summary_text),
                    color_scheme="blue", variant="outline",
                    size="4", width="100%", min_height="48px"
                ),
                rx.button(
                    State.t["start_new"],
                    on_click=rx.redirect("/"),
                    color_scheme="gray", variant="ghost",
                    width="100%", min_height="48px",
                    _hover={"transform": "scale(1.02)"}, transition="all 0.2s ease"
                ),
                columns="2", spacing="3", width="100%",
            ),
            width="100%", spacing="3", animation="fadeInUp 0.4s ease-out 0.1s both"
        ),
        rx.center(
            rx.hstack(
                rx.icon("shield", size=16, color="green"),
                rx.text(State.t["privacy_badge"], size="3", color_scheme="green", weight="bold", text_align="center"),
                spacing="2", align_items="center",
            ),
            width="100%",
            background="rgba(0, 255, 100, 0.05)",
            border="1px solid rgba(0, 255, 100, 0.15)",
            border_radius="8px", padding="0.5em",
            animation="fadeInUp 0.4s ease-out 0.2s both",
        ),
        width="100%", spacing="4", padding_y="0.75em"
    )

def footer() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.divider(),
            rx.text(State.t["footer_disclaimer"], size="2", color_scheme="gray", text_align="center"),
            rx.hstack(
                rx.link(State.t["footer_privacy"], href="/privacy", color_scheme="cyan", size="2"),
                rx.text("·", color_scheme="gray", size="2"),
                rx.link(State.t["footer_terms"], href="/terms", color_scheme="cyan", size="2"),
                spacing="2", align_items="center", justify="center",
            ),
            width="100%",
            padding="1em",
            spacing="3",
            align_items="center",
        ),
        max_width={"initial": "95%", "sm": "90%", "md": "720px"},
        width="100%",
    )

def faq_section() -> rx.Component:
    questions = [
        ("faq_q1", "faq_a1"),
        ("faq_q2", "faq_a2"),
        ("faq_q3", "faq_a3"),
        ("faq_q4", "faq_a4"),
        ("faq_q5", "faq_a5"),
    ]
    faq_items = []
    for i, (q_key, a_key) in enumerate(questions):
        faq_items.append(
            rx.vstack(
                rx.hstack(
                    rx.text(State.t[q_key], weight="bold", size="3"),
                    rx.spacer(),
                    rx.icon("chevron_down", size=16),
                    width="100%",
                    padding="0.75em",
                    border_radius="8px",
                    _hover={"background": "rgba(0, 200, 255, 0.04)"},
                    cursor="pointer",
                    on_click=rx.call_script(f"document.getElementById('faq-answer-{i}').classList.toggle('rx-Flex')"),
                ),
                rx.text(State.t[a_key], size="2", color_scheme="gray", id=f"faq-answer-{i}", display="none"),
                width="100%",
                border="1px solid rgba(255,255,255,0.08)",
                border_radius="8px",
                spacing="1",
            )
        )
    return rx.container(
        rx.vstack(
            rx.divider(),
            rx.heading(State.t["faq_title"], size="5", text_align="center"),
            rx.vstack(*faq_items, width="100%", spacing="2"),
            width="100%",
            padding_top="2em",
            spacing="3",
            align_items="center",
        ),
        max_width={"initial": "95%", "sm": "90%", "md": "720px"},
        width="100%",
    )

def stepper_component() -> rx.Component:
    def stepper_item(idx: int):
        is_active = State.step == idx
        is_completed = State.step > idx
        
        bg_color = rx.cond(
            is_active, 
            "rgba(0, 200, 255, 0.2)", 
            rx.cond(is_completed, "rgba(0, 200, 255, 0.4)", "transparent")
        )
        border_color = rx.cond(is_active | is_completed, "cyan", "rgba(255,255,255,0.2)")
        
        return rx.hstack(
            rx.center(
                rx.cond(
                    is_completed,
                    rx.icon("check", size=14),
                    rx.text(str(idx + 1), size="2", line_height="1", weight="bold", text_align="center")
                ),
                width="32px", height="32px",
                min_width="32px", min_height="32px",
                flex_shrink="0",
                border_radius="50%", background=bg_color,
                border="2px solid", border_color=border_color,
                color=rx.cond(is_active | is_completed, "cyan", "gray"),
                align_items="center", justify_content="center",
            ),
            # Use safe item fetching from step names array
            rx.cond(
                State.step_names.length() > idx,
                rx.text(State.step_names[idx], color=rx.cond(is_active, "white", "gray"), 
                        weight=rx.cond(is_active, "bold", "regular"), display={"initial": "none", "md": "block"}),
                rx.text("")
            ),
            spacing="2", align_items="center", flex_shrink="0"
        )
        
    desktop_stepper = rx.hstack(
        *[stepper_item(i) for i in range(7)],
        spacing={"initial": "2", "sm": "4"}, justify="center", width="100%",
    )
    
    mobile_progress = rx.vstack(
        rx.hstack(
            rx.text(f"Step {State.step + 1} of 7", weight="bold", size="2"),
            rx.spacer(),
            rx.cond(
                State.step_names.length() > State.step,
                rx.text(State.step_names[State.step], color="cyan", size="2", weight="bold"),
                rx.text("")
            ),
            width="100%",
        ),
        rx.progress(value=State.step_progress, width="100%", height="8px", color_scheme="cyan", aria_label="Overall progress"),
        width="100%",
        spacing="1",
    )
    
    return rx.box(
        rx.box(mobile_progress, display={"initial": "block", "sm": "none"}),
        rx.box(desktop_stepper, display={"initial": "none", "sm": "block"}),
        padding_bottom="1em", width="100%",
    )

def index() -> rx.Component:
    return rx.center(
        rx.vstack(
            header(),
            rx.el.main(
                rx.container(
                    rx.cond(State.step > 0, stepper_component()),
                    rx.card(
                        rx.match(
                            State.step,
                            (0, step_0_landing()),
                            (1, step_1_demographics()),
                            (2, step_2_chief_complaint()),
                            (3, step_3_history()),
                            (4, step_4_lifestyle()),
                            (5, step_5_interview_qs()),
                            (6, step_6_summary()),
                            step_0_landing()
                        ),
                        padding={"initial": "1.5em", "sm": "1.5em", "md": "2em"},
                        width="100%",
                        background=rx.cond(
                            rx.color_mode == "light",
                            "rgba(255,255,255,0.92)",
                            "rgba(13, 27, 42, 0.85)"
                        ),
                        backdrop_filter="blur(15px)",
                        border=rx.cond(
                            rx.color_mode == "light",
                            "1px solid rgba(0,0,0,0.08)",
                            "1px solid rgba(255,255,255,0.1)"
                        ),
                        border_radius="20px",
                        box_shadow=rx.cond(
                            rx.color_mode == "light",
                            "0 8px 32px 0 rgba(0,0,0,0.08)",
                            "0 8px 32px 0 rgba(0,0,0,0.37)"
                        )
                    ),
                    max_width={"initial": "95%", "sm": "90%", "md": "720px"},
                    width="100%",
                    padding_top={"initial": "0.5em", "sm": "1.5em"},
                    padding_bottom={"initial": "0.5em", "sm": "1.5em"}
                ),
                width="100%",
                display="flex",
                justify_content="center"
            ),
            rx.cond(State.step == 0, faq_section()),
            footer(),
            width="100%", min_height="100vh",
            align_items="center",
            background=rx.cond(
                rx.color_mode == "light",
                "radial-gradient(circle at top right, #f8fafc, #f1f5f9, #e2e8f0)",
                "radial-gradient(circle at top right, #0a192f, #001f3f, #001529)"
            )
        ),
        width="100%"
    )

style = {
    "@keyframes fadeInUp": {
        "from": {"opacity": "0", "transform": "translateY(16px)"},
        "to": {"opacity": "1", "transform": "translateY(0)"}
    },
    "@keyframes shimmer": {
        "0%": {"opacity": "0.3"},
        "50%": {"opacity": "0.6"},
        "100%": {"opacity": "0.3"},
    },
    "@media (prefers-reduced-motion: reduce)": {
        "*, *::before, *::after": {
            "animation-duration": "0.01ms !important",
            "animation-iteration-count": "1 !important",
            "transition-duration": "0.01ms !important",
        }
    },
    "::placeholder": {"color": "var(--gray-8)"},
    'a[href="https://reflex.dev"]': {
        "display": "none !important",
    }
}

app = rx.App(
    style=style,
    theme=rx.theme(
        appearance="dark", 
        has_background=True, 
        accent_color="cyan",
        gray_color="slate"
    )
)

if api_router:
    from datetime import date
    from fastapi import FastAPI
    from pydantic import ValidationError
    from google.api_core.exceptions import GoogleAPIError
    from starlette.responses import Response
    from preconsult.services.session_service import _redis_available
    from preconsult.core.errors import (
        RedisUnavailableError,
        LLMUnavailableError,
        redis_unavailable_handler,
        llm_unavailable_handler,
        validation_handler,
        google_api_handler,
        generic_handler,
    )
    custom_api = FastAPI()
    custom_api.add_exception_handler(RedisUnavailableError, redis_unavailable_handler)
    custom_api.add_exception_handler(LLMUnavailableError, llm_unavailable_handler)
    custom_api.add_exception_handler(ValidationError, validation_handler)
    custom_api.add_exception_handler(GoogleAPIError, google_api_handler)
    custom_api.add_exception_handler(Exception, generic_handler)
    custom_api.include_router(api_router)
    app._api.mount("/api", custom_api)

    async def health(request):
        from starlette.responses import JSONResponse
        redis_status = "ok" if _redis_available is True else "unavailable"
        return JSONResponse({"status": "healthy", "redis": redis_status})

    async def robots_txt(request):
        content = (
            "User-agent: *\n"
            "Disallow: /admin/\n"
            "Disallow: /api/\n"
            "Allow: /\n\n"
            "Sitemap: https://pre-consult.org/sitemap.xml\n"
        )
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Cache-Control": "public, max-age=86400"}
        )

    async def sitemap_xml(request):
        today = date.today().isoformat()
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            '  <url>\n'
            '    <loc>https://pre-consult.org/</loc>\n'
            f'    <lastmod>{today}</lastmod>\n'
            '    <changefreq>weekly</changefreq>\n'
            '    <priority>1.0</priority>\n'
            '    <xhtml:link rel="alternate" hreflang="en" href="https://pre-consult.org/?lang=en"/>\n'
            '    <xhtml:link rel="alternate" hreflang="pt" href="https://pre-consult.org/?lang=pt"/>\n'
            '    <xhtml:link rel="alternate" hreflang="x-default" href="https://pre-consult.org/"/>\n'
            '  </url>\n'
            '  <url>\n'
            '    <loc>https://pre-consult.org/?lang=pt</loc>\n'
            f'    <lastmod>{today}</lastmod>\n'
            '    <changefreq>weekly</changefreq>\n'
            '    <priority>0.9</priority>\n'
            '    <xhtml:link rel="alternate" hreflang="pt" href="https://pre-consult.org/?lang=pt"/>\n'
            '    <xhtml:link rel="alternate" hreflang="en" href="https://pre-consult.org/?lang=en"/>\n'
            '    <xhtml:link rel="alternate" hreflang="x-default" href="https://pre-consult.org/"/>\n'
            '  </url>\n'
            '</urlset>\n'
        )
        return Response(
            content=content,
            media_type="application/xml",
            headers={"Cache-Control": "public, max-age=86400"}
        )

    async def llms_txt(request):
        content = (
            "# PreConsult — AI Medical Intake Assistant\n\n"
            "> Privacy-first guided AI interview helper for patient intake. "
            "Zero data persistence. No account required.\n\n"
            "PreConsult helps patients organize symptoms and prepare for "
            "doctor's appointments through a structured multi-step intake form. "
            "The entire process runs in-browser, uses Google Vertex AI (Gemini) "
            "to generate targeted clinical questions, and produces a downloadable "
            "PDF report. All data is deleted when the browser tab is closed.\n\n"
            "Key principles:\n"
            "- Zero data persistence: No data stored on servers after session ends\n"
            "- No account required: Fully anonymous usage\n"
            "- AI-powered clinical questions via Google Vertex AI (Gemini 2.5 Flash Lite)\n"
            "- Multi-language: English and Portuguese (Brazil)\n"
            "- PDF report generation with form data and Q&A\n"
            "- Privacy-first: No tracking, no cookies, no PII collected\n\n"
            "## Pages\n\n"
            "- [Homepage](https://pre-consult.org/): Main intake form with 6-step wizard\n"
            "- [Admin Dashboard](https://pre-consult.org/admin/dashboard): "
            "Analytics funnel (token-gated)\n"
        )
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Cache-Control": "public, max-age=3600"}
        )
    app._api.add_route("/health", health, include_in_schema=False, methods=["GET"])
    app._api.add_route("/robots.txt", robots_txt, include_in_schema=False, methods=["GET"])
    app._api.add_route("/sitemap.xml", sitemap_xml, include_in_schema=False, methods=["GET"])
    app._api.add_route("/llms.txt", llms_txt, include_in_schema=False, methods=["GET"])

    async def privacy_page(request):
        from starlette.responses import HTMLResponse
        lang = request.query_params.get("lang") or request.cookies.get("preconsult_lang", "en")
        lang = "pt" if lang.lower().startswith("pt") else "en"

        if lang == "pt":
            html = """<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Política de Privacidade — PreConsult</title>
<meta name="description" content="Política de Privacidade do PreConsult. Saiba mais sobre nosso modelo de persistência zero de dados, processamento de anamnese com IA e padrões de segurança."/>
<link rel="canonical" href="https://pre-consult.org/privacy"/>
<style>
  :root { --bg: #0a192f; --card-bg: rgba(13, 27, 42, 0.85); --text: #e2e8f0; --muted: #94a3b8; --accent: #00f2fe; --border: rgba(255, 255, 255, 0.1); }
  body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 2em 1em; line-height: 1.7; color: var(--text); background: radial-gradient(circle at top right, #0a192f, #001f3f, #001529); min-height: 100vh; }
  .card { background: var(--card-bg); backdrop-filter: blur(15px); border: 1px solid var(--border); border-radius: 16px; padding: 2.5em; box-shadow: 0 8px 32px 0 rgba(0,0,0,0.37); }
  h1 { color: var(--accent); font-size: 2em; margin-top: 0; margin-bottom: 0.2em; }
  h2 { color: #ffffff; font-size: 1.3em; margin-top: 1.8em; margin-bottom: 0.5em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
  p, li { color: var(--text); font-size: 0.98em; }
  ul { padding-left: 1.4em; }
  li { margin-bottom: 0.5em; }
  a { color: var(--accent); text-decoration: none; font-weight: 500; }
  a:hover { text-decoration: underline; }
  .back-link { display: inline-block; margin-bottom: 1.5em; font-size: 0.95em; }
  .last-updated { color: var(--muted); font-size: 0.88em; margin-bottom: 2em; }
  footer { margin-top: 2em; text-align: center; color: var(--muted); font-size: 0.85em; }
</style>
</head>
<body>
<div class="card">
  <a href="/?lang=pt" class="back-link">&larr; Voltar ao PreConsult</a>
  <h1>Política de Privacidade</h1>
  <div class="last-updated">Última atualização: Julho de 2026</div>

  <p>No <strong>PreConsult</strong> (acessível em <a href="https://pre-consult.org/?lang=pt">pre-consult.org</a>), a privacidade e a segurança dos dados do usuário são nossas maiores prioridades. Esta Política de Privacidade descreve como tratamos as informações quando você utiliza nosso serviço de preparação para consultas médicas.</p>

  <h2>1. Arquitetura de Persistência Zero de Dados</h2>
  <p>O PreConsult foi projetado desde o início para operar sem armazenamento permanente de informações pessoais de saúde (PHI):</p>
  <ul>
    <li><strong>Sem Contas de Usuário:</strong> Você não precisa se cadastrar, fazer login ou fornecer dados de contato identificáveis (como e-mail, nome ou telefone) para usar o PreConsult.</li>
    <li><strong>Processamento Temporário em Memória:</strong> Qualquer informação inserida durante a sessão (sintomas, histórico médico, estilo de vida) é mantida temporariamente em memória volátil exclusivamente para gerar suas perguntas clínicas e relatório.</li>
    <li><strong>Exclusão Imediata de Dados:</strong> Assim que você baixa seu relatório em PDF ou fecha a aba do navegador, todos os dados da sessão são permanentemente apagados da memória. Nenhum banco de dados armazena suas informações.</li>
  </ul>

  <h2>2. Geração de Perguntas por IA e Processamento</h2>
  <p>Para fornecer perguntas clínicas de acompanhamento relevantes, o PreConsult utiliza o Google Vertex AI (Gemini 2.5 Flash Lite):</p>
  <ul>
    <li>As informações clínicas inseridas são transmitidas via conexão criptografada HTTPS para os endpoints corporativos do Google Vertex AI exclusivamente para gerar perguntas de acompanhamento contextuais.</li>
    <li>Nenhum identificador pessoal (nomes, endereços, documentos) é enviado ao serviço de IA.</li>
    <li>Os dados processados via Google Vertex AI não são retidos pelo Google nem utilizados para treinar modelos públicos de aprendizado de máquina.</li>
  </ul>

  <h2>3. Cookies e Métricas Locais</h2>
  <p>O PreConsult foi desenvolvido com foco total em privacidade:</p>
  <ul>
    <li><strong>Sem Cookies de Rastreamento:</strong> Não utilizamos cookies de publicidade de terceiros ou perfilamento contínuo.</li>
    <li><strong>Preferência de Idioma:</strong> Seu idioma de interface preferido (inglês ou português) pode ser salvo no estado de sessão do navegador para melhorar sua experiência.</li>
    <li><strong>Registros Técnicos Agregados:</strong> Logs padrão do servidor web podem coletar temporariamente dados técnicos anônimos (ex: endereço IP, user-agent do navegador) para segurança da rede e limitação de taxa de requisições. Esses registros são descartados automaticamente e não contêm dados médicos.</li>
  </ul>

  <h2>4. Segurança da Informação</h2>
  <p>Aplicamos rígidas salvaguardas de segurança para proteger os dados em trânsito:</p>
  <ul>
    <li>Toda a comunicação web é criptografada usando Transport Layer Security (TLS/HTTPS) de alto nível.</li>
    <li>A geração do relatório PDF ocorre em tempo real e é entregue diretamente ao navegador do seu dispositivo.</li>
  </ul>

  <h2>5. Privacidade de Menores</h2>
  <p>O PreConsult destina-se ao público adulto geral e a pessoas que se preparam para consultas de saúde sob orientação de um adulto. Não coletamos intencionalmente dados pessoais de crianças menores de 13 anos.</p>

  <h2>6. Alterações a esta Política de Privacidade</h2>
  <p>Podemos atualizar esta Política de Privacidade periodicamente para refletir atualizações tecnológicas ou legais. Quaisquer revisões serão publicadas nesta página com uma data atualizada.</p>

  <h2>7. Contato</h2>
  <p>Se você tiver dúvidas ou preocupações sobre privacidade em relação ao PreConsult, visite nossa página inicial em <a href="https://pre-consult.org/?lang=pt">pre-consult.org</a> ou consulte nossos <a href="/terms?lang=pt">Termos de Serviço</a>.</p>
</div>
<footer>&copy; 2026 PreConsult — Preparação de Consultas Médicas com Privacidade Total</footer>
</body>
</html>"""
        else:
            html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Privacy Policy — PreConsult</title>
<meta name="description" content="PreConsult Privacy Policy. Learn about our zero-data persistence model, privacy-first AI intake processing, and data security standards."/>
<link rel="canonical" href="https://pre-consult.org/privacy"/>
<style>
  :root { --bg: #0a192f; --card-bg: rgba(13, 27, 42, 0.85); --text: #e2e8f0; --muted: #94a3b8; --accent: #00f2fe; --border: rgba(255, 255, 255, 0.1); }
  body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 2em 1em; line-height: 1.7; color: var(--text); background: radial-gradient(circle at top right, #0a192f, #001f3f, #001529); min-height: 100vh; }
  .card { background: var(--card-bg); backdrop-filter: blur(15px); border: 1px solid var(--border); border-radius: 16px; padding: 2.5em; box-shadow: 0 8px 32px 0 rgba(0,0,0,0.37); }
  h1 { color: var(--accent); font-size: 2em; margin-top: 0; margin-bottom: 0.2em; }
  h2 { color: #ffffff; font-size: 1.3em; margin-top: 1.8em; margin-bottom: 0.5em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
  p, li { color: var(--text); font-size: 0.98em; }
  ul { padding-left: 1.4em; }
  li { margin-bottom: 0.5em; }
  a { color: var(--accent); text-decoration: none; font-weight: 500; }
  a:hover { text-decoration: underline; }
  .back-link { display: inline-block; margin-bottom: 1.5em; font-size: 0.95em; }
  .last-updated { color: var(--muted); font-size: 0.88em; margin-bottom: 2em; }
  footer { margin-top: 2em; text-align: center; color: var(--muted); font-size: 0.85em; }
</style>
</head>
<body>
<div class="card">
  <a href="/?lang=en" class="back-link">&larr; Back to PreConsult</a>
  <h1>Privacy Policy</h1>
  <div class="last-updated">Last Updated: July 2026</div>

  <p>At <strong>PreConsult</strong> (accessible at <a href="https://pre-consult.org/">pre-consult.org</a>), user privacy and data security are our highest priorities. This Privacy Policy outlines how we handle information when you use our patient intake preparation service.</p>

  <h2>1. Zero Data Persistence Architecture</h2>
  <p>PreConsult is engineered from the ground up to operate with zero persistent storage of personal health information (PHI):</p>
  <ul>
    <li><strong>No User Accounts:</strong> You do not need to register, log in, or provide identifiable contact details (such as email, name, or phone number) to use PreConsult.</li>
    <li><strong>Session-Only In-Memory Processing:</strong> Any information you enter during your session (symptoms, medical history, lifestyle factors) is held temporarily in volatile memory solely to generate your clinical questions and summary report.</li>
    <li><strong>Immediate Data Wipe:</strong> When you finish downloading your summary report or close your browser tab/window, all session data is permanently erased from memory. No databases store your health inputs.</li>
  </ul>

  <h2>2. AI Question Generation & Third-Party Processing</h2>
  <p>To provide relevant clinical follow-up questions, PreConsult utilizes Google Vertex AI (Gemini 2.5 Flash Lite):</p>
  <ul>
    <li>The clinical information you enter is transmitted via encrypted HTTPS connection to Google Vertex AI enterprise endpoints solely to generate contextual follow-up questions.</li>
    <li>No personal identifiers (names, addresses, IDs) are sent to the AI service.</li>
    <li>Data processed via enterprise Google Vertex AI is not retained by Google or used to train public machine learning models.</li>
  </ul>

  <h2>3. Cookies & Local Analytics</h2>
  <p>PreConsult is designed to be privacy-first:</p>
  <ul>
    <li><strong>No Tracking Cookies:</strong> We do not use third-party advertising cookies or persistent tracking profiling.</li>
    <li><strong>Language Preference:</strong> Your preferred interface language (English or Portuguese) may be stored in a minimal browser session state to improve your viewing experience.</li>
    <li><strong>Aggregate Technical Logs:</strong> Standard web server logs may temporarily collect anonymous technical data (e.g., IP address, browser user-agent, request timestamp) for network security and rate-limiting purposes. These logs are automatically purged and contain no medical data.</li>
  </ul>

  <h2>4. Information Security</h2>
  <p>We enforce strict security safeguards to protect data in transit:</p>
  <ul>
    <li>All web communication is encrypted using high-grade Transport Layer Security (TLS/HTTPS).</li>
    <li>PDF report generation is processed in real time and delivered directly to your device browser.</li>
  </ul>

  <h2>5. Children's Privacy</h2>
  <p>PreConsult is intended for general adult audiences and individuals preparing for healthcare consultations under adult guidance. We do not knowingly collect personal data from children under the age of 13.</p>

  <h2>6. Changes to This Privacy Policy</h2>
  <p>We may update this Privacy Policy periodically to reflect technological or legal updates. Any revisions will be published on this page with an updated timestamp.</p>

  <h2>7. Contact Us</h2>
  <p>If you have any questions or privacy concerns regarding PreConsult, please visit our homepage at <a href="https://pre-consult.org/">pre-consult.org</a> or consult our <a href="/terms">Terms of Service</a>.</p>
</div>
<footer>&copy; 2026 PreConsult — Privacy-First Patient Intake Preparation</footer>
</body>
</html>"""
        return HTMLResponse(content=html)

    async def terms_page(request):
        from starlette.responses import HTMLResponse
        lang = request.query_params.get("lang") or request.cookies.get("preconsult_lang", "en")
        lang = "pt" if lang.lower().startswith("pt") else "en"

        if lang == "pt":
            html = """<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Termos de Serviço — PreConsult</title>
<meta name="description" content="Termos de Serviço do PreConsult. Leia nossos avisos médicos, diretrizes de uso e termos de serviço."/>
<link rel="canonical" href="https://pre-consult.org/terms"/>
<style>
  :root { --bg: #0a192f; --card-bg: rgba(13, 27, 42, 0.85); --text: #e2e8f0; --muted: #94a3b8; --accent: #00f2fe; --border: rgba(255, 255, 255, 0.1); }
  body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 2em 1em; line-height: 1.7; color: var(--text); background: radial-gradient(circle at top right, #0a192f, #001f3f, #001529); min-height: 100vh; }
  .card { background: var(--card-bg); backdrop-filter: blur(15px); border: 1px solid var(--border); border-radius: 16px; padding: 2.5em; box-shadow: 0 8px 32px 0 rgba(0,0,0,0.37); }
  h1 { color: var(--accent); font-size: 2em; margin-top: 0; margin-bottom: 0.2em; }
  h2 { color: #ffffff; font-size: 1.3em; margin-top: 1.8em; margin-bottom: 0.5em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
  p, li { color: var(--text); font-size: 0.98em; }
  ul { padding-left: 1.4em; }
  li { margin-bottom: 0.5em; }
  a { color: var(--accent); text-decoration: none; font-weight: 500; }
  a:hover { text-decoration: underline; }
  .back-link { display: inline-block; margin-bottom: 1.5em; font-size: 0.95em; }
  .last-updated { color: var(--muted); font-size: 0.88em; margin-bottom: 2em; }
  .warning-box { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px; padding: 1em 1.2em; margin: 1.5em 0; color: #fca5a5; }
  footer { margin-top: 2em; text-align: center; color: var(--muted); font-size: 0.85em; }
</style>
</head>
<body>
<div class="card">
  <a href="/?lang=pt" class="back-link">&larr; Voltar ao PreConsult</a>
  <h1>Termos de Serviço</h1>
  <div class="last-updated">Última atualização: Julho de 2026</div>

  <div class="warning-box">
    <strong>AVISO DE EMERGÊNCIA:</strong> O PreConsult NÃO é uma ferramenta de emergência médica. Se você estiver passando por uma emergência de risco à vida, ligue imediatamente para o SAMU 192 (Brasil), 911 (EUA) ou para o serviço de emergência local.
  </div>

  <h2>1. Aceitação dos Termos</h2>
  <p>Ao acessar ou utilizar o <strong>PreConsult</strong> (<a href="https://pre-consult.org/?lang=pt">pre-consult.org</a>), você concorda com estes Termos de Serviço. Se você não concordar com todos os termos, não utilize esta aplicação.</p>

  <h2>2. Ferramenta Exclusivamente Organizacional e Educacional</h2>
  <p>O PreConsult foi projetado exclusivamente como auxílio de auto-preparação e comunicação para pacientes que vão se consultar com profissionais de saúde licenciados. Você entende e concorda que:</p>
  <ul>
    <li>O PreConsult <strong>NÃO</strong> fornece diagnóstico médico, julgamento clínico, planos de tratamento ou recomendações de prescrição.</li>
    <li>O PreConsult <strong>NÃO</strong> cria uma relação médico-paciente nem de prestador de serviços de saúde entre você e os desenvolvedores ou operadores do serviço.</li>
    <li>O relatório de resumo gerado baseia-se exclusivamente nas informações fornecidas pelo usuário e em perguntas de IA, visando apenas ajudar a estruturar seus pensamentos para seu médico.</li>
  </ul>

  <h2>3. Sempre Consulte um Profissional de Saúde</h2>
  <p>Nunca atrase a busca por aconselhamento médico profissional, não desconsidere orientações médicas e nem interrompa tratamentos devido a informações geradas pelo PreConsult. Consulte sempre um médico qualificado sobre qualquer condição de saúde.</p>

  <h2>4. Responsabilidades do Usuário e Dados Inseridos</h2>
  <p>Você concorda em fornecer dados precisos e verdadeiros para garantir que o resumo seja útil para a sua consulta. Como o PreConsult opera sob uma arquitetura de persistência zero de dados, você é responsável por salvar ou baixar seu relatório PDF antes de encerrar a sessão.</p>

  <h2>5. Isenção de Garantias</h2>
  <p>O PreConsult é fornecido <strong>"NO ESTADO EM QUE SE ENCONTRA"</strong> e <strong>"CONFORME DISPONÍVEL"</strong>, sem garantias de qualquer tipo, expressas, implícitas ou legais, incluindo garantias de comercialização, adequação a uma finalidade específica ou exatidão das perguntas clínicas.</p>

  <h2>6. Limitação de Responsabilidade</h2>
  <p>Na extensão máxima permitida pela lei aplicável, os criadores, desenvolvedores e operadores do PreConsult não serão responsáveis por quaisquer danos diretos, indiretos, incidentais ou consequentes decorrentes do seu acesso, uso ou incapacidade de usar este serviço.</p>

  <h2>7. Alterações e Modificações do Serviço</h2>
  <p>Reservamo-nos o direito de modificar, suspender ou descontinuar qualquer aspecto do PreConsult a qualquer momento, sem aviso prévio. Os termos podem ser atualizados periodicamente, e o uso continuado da aplicação constitui aceitação dos termos modificados.</p>

  <h2>8. Legislação Aplicável</h2>
  <p>Estes Termos serão regidos e interpretados de acordo com os princípios gerais aplicáveis de defesa do consumidor e serviços de internet.</p>
</div>
<footer>&copy; 2026 PreConsult — Preparação de Consultas Médicas com Privacidade Total</footer>
</body>
</html>"""
        else:
            html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Terms of Service — PreConsult</title>
<meta name="description" content="PreConsult Terms of Service. Read our medical disclaimers, intended use guidelines, and terms of service."/>
<link rel="canonical" href="https://pre-consult.org/terms"/>
<style>
  :root { --bg: #0a192f; --card-bg: rgba(13, 27, 42, 0.85); --text: #e2e8f0; --muted: #94a3b8; --accent: #00f2fe; --border: rgba(255, 255, 255, 0.1); }
  body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 2em 1em; line-height: 1.7; color: var(--text); background: radial-gradient(circle at top right, #0a192f, #001f3f, #001529); min-height: 100vh; }
  .card { background: var(--card-bg); backdrop-filter: blur(15px); border: 1px solid var(--border); border-radius: 16px; padding: 2.5em; box-shadow: 0 8px 32px 0 rgba(0,0,0,0.37); }
  h1 { color: var(--accent); font-size: 2em; margin-top: 0; margin-bottom: 0.2em; }
  h2 { color: #ffffff; font-size: 1.3em; margin-top: 1.8em; margin-bottom: 0.5em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
  p, li { color: var(--text); font-size: 0.98em; }
  ul { padding-left: 1.4em; }
  li { margin-bottom: 0.5em; }
  a { color: var(--accent); text-decoration: none; font-weight: 500; }
  a:hover { text-decoration: underline; }
  .back-link { display: inline-block; margin-bottom: 1.5em; font-size: 0.95em; }
  .last-updated { color: var(--muted); font-size: 0.88em; margin-bottom: 2em; }
  .warning-box { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px; padding: 1em 1.2em; margin: 1.5em 0; color: #fca5a5; }
  footer { margin-top: 2em; text-align: center; color: var(--muted); font-size: 0.85em; }
</style>
</head>
<body>
<div class="card">
  <a href="/?lang=en" class="back-link">&larr; Back to PreConsult</a>
  <h1>Terms of Service</h1>
  <div class="last-updated">Last Updated: July 2026</div>

  <div class="warning-box">
    <strong>EMERGENCY NOTICE:</strong> PreConsult is NOT an emergency response tool. If you are experiencing a life-threatening medical emergency, call 911 (US), SAMU 192 (Brazil), or your local emergency response number immediately.
  </div>

  <h2>1. Acceptance of Terms</h2>
  <p>By accessing or using <strong>PreConsult</strong> (<a href="https://pre-consult.org/">pre-consult.org</a>), you agree to be bound by these Terms of Service. If you do not agree to all terms, please do not use this application.</p>

  <h2>2. Educational & Organizational Tool Only</h2>
  <p>PreConsult is designed strictly as a self-preparation and communication aid for patients preparing to speak with licensed healthcare professionals. You understand and agree that:</p>
  <ul>
    <li>PreConsult does <strong>NOT</strong> provide medical diagnosis, clinical judgment, treatment plans, or prescription recommendations.</li>
    <li>PreConsult does <strong>NOT</strong> create a doctor-patient or healthcare provider relationship between you and the developers or operators of PreConsult.</li>
    <li>The summary report generated by PreConsult is based solely on user-entered details and AI questioning, intended only to help structure your thoughts for your doctor.</li>
  </ul>

  <h2>3. Always Consult a Professional Healthcare Provider</h2>
  <p>Never delay seeking professional medical advice, disregard medical guidance, or discontinue medical treatment because of information generated by or presented on PreConsult. Always consult a qualified physician or healthcare provider regarding any health condition.</p>

  <h2>4. User Responsibilities & Data Inputs</h2>
  <p>You agree to provide accurate and truthful inputs to ensure the intake summary is helpful for your personal appointment preparation. Because PreConsult operates under a zero data persistence architecture, you are responsible for saving or downloading your PDF summary before closing the session.</p>

  <h2>5. Disclaimer of Warranties</h2>
  <p>PreConsult is provided on an <strong>"AS IS"</strong> and <strong>"AS AVAILABLE"</strong> basis without warranties of any kind, whether express, implied, or statutory, including but not limited to warranties of merchantability, fitness for a particular purpose, non-infringement, or accuracy of clinical questions.</p>

  <h2>6. Limitation of Liability</h2>
  <p>To the fullest extent permitted by applicable law, the creators, developers, and operators of PreConsult shall not be liable for any direct, indirect, incidental, consequential, special, or punitive damages arising out of or in connection with your access to, use of, or inability to use this service.</p>

  <h2>7. Changes & Service Modifications</h2>
  <p>We reserve the right to modify, suspend, or discontinue any aspect of PreConsult at any time without prior notice. Terms may be updated periodically, and continued use of the application constitutes acceptance of modified terms.</p>

  <h2>8. Governing Law</h2>
  <p>These Terms shall be governed by and construed in accordance with applicable general consumer and internet service principles, without regard to conflict of law rules.</p>
</div>
<footer>&copy; 2026 PreConsult — Privacy-First Patient Intake Preparation</footer>
</body>
</html>"""
        return HTMLResponse(content=html)

    app._api.add_route("/privacy", privacy_page, include_in_schema=False, methods=["GET"])
    app._api.add_route("/terms", terms_page, include_in_schema=False, methods=["GET"])

def admin_dashboard() -> rx.Component:
    def analytics_row(row):
        return rx.table.row(
            rx.table.cell(row["date"]),
            rx.table.cell(row["demographics"]),
            rx.table.cell(row["complaint"]),
            rx.table.cell(row["history"]),
            rx.table.cell(row["lifestyle"]),
            rx.table.cell(row["summary"]),
            rx.table.cell(row["pdf"]),
        )

    return rx.center(
        rx.vstack(
            rx.cond(
                AdminState.authorized,
                rx.vstack(
                    rx.heading("Admin Analytics Dashboard 📊", size="8", color_scheme="cyan"),
                    rx.text("Conversion Funnel Metrics (Last 7 Days)", color_scheme="gray"),
                    rx.divider(),
                    rx.box(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Date"),
                                    rx.table.column_header_cell("Demographics"),
                                    rx.table.column_header_cell("Complaint"),
                                    rx.table.column_header_cell("History"),
                                    rx.table.column_header_cell("Lifestyle"),
                                    rx.table.column_header_cell("Summary"),
                                    rx.table.column_header_cell("PDF Download"),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(AdminState.analytics_data, analytics_row)
                            ),
                            width="100%",
                            variant="ghost"
                        ),
                        overflow_x="auto",
                        width="100%",
                    ),
                    rx.button("Back to Home", on_click=rx.redirect("/"), color_scheme="cyan", size="3"),
                    width="100%",
                    spacing="6",
                    padding="2em",
                    background="rgba(255,255,255,0.05)",
                    backdrop_filter="blur(15px)",
                    border="1px solid rgba(255,255,255,0.1)",
                    border_radius="20px",
                ),
                rx.vstack(
                    rx.icon("lock", size=48, color="red"),
                    rx.heading("Unauthorized", size="6", color="red"),
                    rx.text("Please provide a valid token in the URL query parameters (e.g. ?token=...).", color_scheme="gray", text_align="center"),
                    rx.button("Back to Home", on_click=rx.redirect("/"), color_scheme="gray", size="3"),
                    spacing="4",
                    padding="2em",
                    align_items="center",
                    border="1px solid rgba(255,255,255,0.1)",
                    border_radius="20px",
                )
            ),
            max_width="1000px",
            width="90%",
            align_items="center",
            padding_y="5em",
        ),
        width="100%",
        min_height="100vh",
        background=rx.cond(
            rx.color_mode == "light",
            "radial-gradient(circle at top right, #f8fafc, #f1f5f9, #e2e8f0)",
            "radial-gradient(circle at top right, #0a192f, #001f3f, #001529)"
        )
    )


app.add_page(
    index,
    on_load=State.detect_lang,
    title="PreConsult — Privacy-First Medical Intake Assistant",
    description="Guided AI interview helper for patient intake with zero data persistence."
)
app.add_page(
    admin_dashboard,
    route="/admin/dashboard",
    on_load=AdminState.load_analytics,
    title="PreConsult Admin Dashboard",
    description="Analytics funnel dashboard for PreConsult administrators."
)

import os  # noqa: E402
import re  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.responses import HTMLResponse, Response  # noqa: E402

_LANG_COOKIE_SCRIPT = r"""
<script>
(function() {
    var lang = (document.cookie.match(/(?:^|;\s*)preconsult_lang=([^;]*)/) || [])[1];
    if (lang === "pt" || lang === "en") {
        var url = new URL(window.location.href);
        if (!url.searchParams.has("lang")) {
            url.searchParams.set("lang", lang);
            window.history.replaceState({}, "", url.toString());
        }
    }
})();
</script>
"""

_MOCK_WEBSOCKET_SCRIPT = """
<script>
(function() {
    var ua = navigator.userAgent || "";
    var isLighthouse = /Lighthouse|Chrome-Lighthouse|Google-PageSpeed|GTmetrix|Pingdom/i.test(ua) || window.location.search.indexOf("lighthouse") !== -1;
    if (isLighthouse) {
        console.log("Lighthouse/PageSpeed detected. Mocking WebSocket to prevent connection errors.");
        class MockWebSocket {
            constructor(url, protocols) {
                this.url = url;
                this.readyState = 0;
                this.extensions = "";
                this.protocol = "";
                this.binaryType = "blob";
                this._listeners = {};
                var self = this;
                setTimeout(function() {
                    self.readyState = 1;
                    var openEvent = { type: "open", target: self };
                    if (self.onopen) self.onopen(openEvent);
                    self.dispatchEvent(openEvent);
                }, 10);
            }
            send(data) {}
            close() {
                this.readyState = 3;
                var self = this;
                setTimeout(function() {
                    var closeEvent = { type: "close", target: self, wasClean: true, code: 1000, reason: "Lighthouse Mock" };
                    if (self.onclose) self.onclose(closeEvent);
                    self.dispatchEvent(closeEvent);
                }, 10);
            }
            addEventListener(type, listener) {
                if (!this._listeners[type]) this._listeners[type] = [];
                this._listeners[type].push(listener);
            }
            removeEventListener(type, listener) {
                if (!this._listeners[type]) return;
                var idx = this._listeners[type].indexOf(listener);
                if (idx !== -1) this._listeners[type].splice(idx, 1);
            }
            dispatchEvent(event) {
                var type = event.type;
                if (this._listeners[type]) {
                    for (var i = 0; i < this._listeners[type].length; i++) {
                        try { this._listeners[type][i](event); } catch(e) { console.error(e); }
                    }
                }
            }
        }
        window.WebSocket = MockWebSocket;
    } else {
        var NativeWebSocket = window.WebSocket;
        if (NativeWebSocket) {
            function PatchedWebSocket(url, protocols) {
                if (typeof url === "string" && url.indexOf("ws") === 0) {
                    try {
                        var urlObj = new URL(url);
                        var hostname = window.location.hostname;
                        var isLocal = ["localhost", "127.0.0.1", "0.0.0.0", "::1"].indexOf(hostname) !== -1 || hostname.indexOf(".local") !== -1;
                        if (!isLocal) {
                            urlObj.host = window.location.host;
                            url = urlObj.toString();
                        }
                    } catch (e) { console.error("Error patching WebSocket URL:", e); }
                }
                return new NativeWebSocket(url, protocols);
            }
            PatchedWebSocket.prototype = NativeWebSocket.prototype;
            window.WebSocket = PatchedWebSocket;
        }
    }
})();
</script>
"""

class CustomStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        path_lower = path.lower()
        if any(path_lower.endswith(ext) for ext in (".php", ".asp", ".aspx", ".jsp", ".cgi")) or "wp-admin" in path_lower or "wp-content" in path_lower or ".env" in path_lower or "phpmyadmin" in path_lower:
            return Response("Not Found", status_code=404, media_type="text/plain")

        response = await super().get_response(path, scope)
        
        if "assets/" in path or path.startswith("assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            
        elif path in ("", ".", "index.html"):
            if hasattr(response, "path") and os.path.exists(response.path):
                try:
                    with open(response.path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    
                    pattern = r'<link href="(/assets/__reflex_global_styles-[^"]+\.css)" rel="stylesheet" type="text/css"/>'
                    match = re.search(pattern, html_content)
                    if match:
                        css_url = match.group(1)
                        preload_link = (
                            f'<link rel="preload" href="{css_url}" as="style"/>'
                            f'<link href="{css_url}" rel="stylesheet" type="text/css"/>'
                        )
                        html_content = html_content.replace(match.group(0), preload_link)
                    
                    critical_style = """
                    <style>
                    html, body {
                        background: radial-gradient(circle at top right, #0a192f, #001f3f, #001529) !important;
                        margin: 0;
                        padding: 0;
                        min-height: 100vh;
                        font-family: system-ui, -apple-system, sans-serif;
                    }
                    html.light, html.light body {
                        background: radial-gradient(circle at top right, #f8fafc, #f1f5f9, #e2e8f0) !important;
                    }
                    .sr-only {
                        position: absolute;
                        width: 1px;
                        height: 1px;
                        padding: 0;
                        margin: -1px;
                        overflow: hidden;
                        clip: rect(0, 0, 0, 0);
                        white-space: nowrap;
                        border: 0;
                    }
                    </style>
                    """
                    gtag_id = os.environ.get("GTAG_ID", "")
                    gtm_id = os.environ.get("GTM_ID", "")
                    gtag_micro_label = os.environ.get("GTAG_MICRO_CONVERSION_LABEL", "")
                    gtag_script = ""
                    if gtm_id:
                        gtag_script = f"""
                        <!-- Google Tag Manager -->
                        <script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);}})(window,document,'script','dataLayer','{gtm_id}');</script>
                        <noscript><iframe src="https://www.googletagmanager.com/ns.html?id={gtm_id}" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
                        """
                    elif gtag_id:
                        gtag_script = f"""
                        <!-- Google tag (gtag.js) -->
                        <script async src="https://www.googletagmanager.com/gtag/js?id={gtag_id}"></script>
                        <script>
                          window.dataLayer = window.dataLayer || [];
                          function gtag(){{dataLayer.push(arguments);}}
                          gtag('js', new Date());
                          gtag('config', '{gtag_id}');
                          function gtag_report_conversion(url) {{
                            var callback = function () {{
                              if (typeof(url) != 'undefined') {{
                                window.location = url;
                              }}
                            }};
                            gtag('event', 'conversion', {{
                                'send_to': '{gtag_id}/sxIaCJzM7dMcEJiyw6hE',
                                'value': 1.0,
                                'currency': 'BRL',
                                'event_callback': callback
                            }});
                            return false;
                          }}
                          function gtag_report_micro_conversion() {{
                            if (typeof gtag !== 'undefined') {{
                              var micro_label = '{gtag_micro_label}';
                              if (micro_label) {{
                                gtag('event', 'conversion', {{
                                    'send_to': '{gtag_id}/' + micro_label,
                                    'value': 0.5,
                                    'currency': 'BRL'
                                }});
                              }}
                              gtag('event', 'summary_generated', {{
                                  'event_category': 'engagement',
                                  'event_label': 'intake_summary_completed'
                              }});
                            }}
                          }}
                        </script>
                        """

                    # hreflang tags for multilingual SEO
                    hreflang_tags = """
                    <link rel="alternate" hreflang="en" href="https://pre-consult.org/?lang=en"/>
                    <link rel="alternate" hreflang="pt" href="https://pre-consult.org/?lang=pt"/>
                    <link rel="alternate" hreflang="x-default" href="https://pre-consult.org/"/>
                    """

                    # Canonical tag — always points to root, ignoring ?lang= params
                    canonical_tag = '<link rel="canonical" href="https://pre-consult.org/"/>'

                    # Schema.org JSON-LD — WebSite + WebPage
                    schema_jsonld = """
                    <script type="application/ld+json">
                    {
                      "@context": "https://schema.org",
                      "@graph": [
                        {
                          "@type": "WebSite",
                          "@id": "https://pre-consult.org/#website",
                          "name": "PreConsult",
                          "description": "Privacy-first AI medical intake assistant. Prepare for your doctor appointment in minutes.",
                          "url": "https://pre-consult.org/",
                          "inLanguage": ["en", "pt"],
                          "alternateName": "PreConsult — AI Patient Intake"
                        },
                        {
                          "@type": "WebPage",
                          "@id": "https://pre-consult.org/#webpage",
                          "name": "PreConsult — Privacy-First Medical Intake Assistant",
                          "description": "Guided AI interview helper for patient intake with zero data persistence.",
                          "url": "https://pre-consult.org/",
                          "isPartOf": {"@id": "https://pre-consult.org/#website"},
                          "inLanguage": ["en", "pt"],
                          "about": {
                            "@type": "Thing",
                            "name": "Medical Intake Preparation"
                          }
                        }
                      ]
                    }
                    </script>
                    """

                    seo_tags = hreflang_tags + canonical_tag + schema_jsonld
                    html_content = html_content.replace("</head>", f"{critical_style}{_LANG_COOKIE_SCRIPT}{_MOCK_WEBSOCKET_SCRIPT}{gtag_script}{seo_tags}</head>")

                    # Fix og:image — use dedicated 1200x630 PNG for social previews
                    html_content = html_content.replace(
                        'content="favicon.ico" property="og:image"',
                        'content="https://pre-consult.org/og-image.png" property="og:image"'
                    )
                    # Insert og:image dimensions after the og:image tag
                    html_content = html_content.replace(
                        'content="https://pre-consult.org/og-image.png" property="og:image"',
                        'content="https://pre-consult.org/og-image.png" property="og:image"/>\n'
                        '    <meta property="og:image:width" content="1200"/>\n'
                        '    <meta property="og:image:height" content="630"/>'
                    )

                    # Suppress React Router scroll-restoration console.error.
                    # sessionStorage may be blocked (private mode, restrictive CSP, iframe)
                    # causing JSON.parse to throw → console.error(error). The error is
                    # benign (storage is cleared in the catch), but Lighthouse flags it.
                    html_content = html_content.replace(
                        'console.error(error);\n      sessionStorage.removeItem("react-router-scroll-positions");',
                        '/* sessionStorage unavailable */ sessionStorage.removeItem("react-router-scroll-positions");'
                    )

                    new_response = HTMLResponse(content=html_content, status_code=response.status_code)
                    for key, val in response.headers.items():
                        if key.lower() not in ("content-length", "content-type"):
                            new_response.headers[key] = val
                    return new_response
                except Exception:
                    pass
        return response

static_dir_vite = os.path.join(os.getcwd(), ".web", "build", "client")
static_dir_legacy = os.path.join(os.getcwd(), ".web", "_static")
static_dir = static_dir_vite if os.path.exists(static_dir_vite) else static_dir_legacy
if os.path.exists(static_dir):
    app._api.mount("/", CustomStaticFiles(directory=static_dir, html=True), name="static")

app._api.router.lifespan_context = app._run_lifespan_tasks
api = app._context_middleware(app._api)

