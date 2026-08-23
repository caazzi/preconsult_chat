import os
import asyncio
import logging
import time
import reflex as rx
from starlette.middleware.gzip import GZipMiddleware
from .state import State, AdminState
from preconsult.core.observability import log_event, new_request_id
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
            width="100%", max_height={"initial": "340px", "sm": "380px"},
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
                    on_click=State.reset_intake,
                    color_scheme="gray", variant="ghost",
                    width="100%", min_height="48px",
                    _hover={"transform": "scale(1.02)"}, transition="all 0.2s ease"
                ),
                columns={"initial": "1", "sm": "2"}, spacing="3", width="100%",
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
            rx.accordion.item(
                rx.accordion.trigger(
                    rx.hstack(
                        rx.text(State.t[q_key], weight="bold", size="3"),
                        rx.spacer(),
                        rx.icon("chevron_down", size=16),
                        width="100%",
                        align_items="center",
                    ),
                    width="100%",
                    padding="0.85em 1em",
                    cursor="pointer",
                    _hover={"background": "rgba(0, 200, 255, 0.04)"},
                    border_radius="8px",
                ),
                rx.accordion.content(
                    rx.text(State.t[a_key], size="2", color_scheme="gray", padding="0.5em 1em 1em 1em"),
                ),
                value=f"faq-{i}",
                border="1px solid rgba(255,255,255,0.08)",
                border_radius="8px",
                width="100%",
            )
        )
    return rx.container(
        rx.vstack(
            rx.divider(),
            rx.heading(State.t["faq_title"], size="5", text_align="center"),
            rx.accordion.root(
                *faq_items,
                type="single",
                collapsible=True,
                width="100%",
            ),
            width="100%",
            padding_top="2em",
            spacing="3",
            align_items="center",
        ),
        max_width={"initial": "95%", "sm": "90%", "md": "720px"},
        width="100%",
        min_height="360px",
        style={"contain": "layout inline-size", "content_visibility": "auto"},
    )

def stepper_component() -> rx.Component:
    def desktop_step_item(idx: int):
        is_active = (State.active_step_index == idx) & (State.step < 6)
        is_completed = (State.active_step_index > idx) | (State.step == 6)
        
        bg_color = rx.cond(
            is_active, 
            "rgba(0, 242, 254, 0.25)", 
            rx.cond(is_completed, "rgba(0, 242, 254, 0.4)", "rgba(255,255,255,0.03)")
        )
        border_color = rx.cond(
            is_active, 
            "#00f2fe", 
            rx.cond(is_completed, "#00c8ff", "rgba(255,255,255,0.18)")
        )
        box_shadow = rx.cond(
            is_active,
            "0 0 12px rgba(0, 242, 254, 0.4)",
            "none"
        )
        text_color = rx.cond(is_active | is_completed, "#00f2fe", "rgba(255,255,255,0.5)")
        
        circle_badge = rx.box(
            rx.cond(
                is_completed,
                rx.icon("check", size=14, stroke_width=3),
                rx.text(str(idx + 1), size="2", line_height="1", weight="bold", text_align="center")
            ),
            width="32px",
            height="32px",
            min_width="32px",
            min_height="32px",
            style={
                "aspect_ratio": "1 / 1",
                "flex_shrink": 0,
                "display": "flex",
                "align_items": "center",
                "justify_content": "center",
            },
            border_radius="50%",
            background=bg_color,
            border="2px solid",
            border_color=border_color,
            box_shadow=box_shadow,
            color=text_color,
            transition="all 0.2s ease-in-out",
        )
        
        # Connecting line to next step (if not last step)
        connecting_line = rx.cond(
            idx < 4,
            rx.box(
                flex="1",
                height="2px",
                min_width="12px",
                background=rx.cond(
                    (State.active_step_index > idx) | (State.step == 6),
                    "linear-gradient(90deg, #00c8ff, #00f2fe)",
                    "rgba(255, 255, 255, 0.12)"
                ),
                margin_x="4px",
                transition="all 0.3s ease",
            ),
            rx.box()
        )
        
        step_label = rx.cond(
            State.step_names.length() > idx,
            rx.text(
                State.step_names[idx],
                color=rx.cond(is_active, "white", rx.cond(is_completed, "#e2e8f0", "rgba(255,255,255,0.4)")),
                weight=rx.cond(is_active, "bold", "regular"),
                size="2",
                white_space="nowrap",
            ),
            rx.text("")
        )

        return rx.hstack(
            rx.hstack(
                circle_badge,
                step_label,
                spacing="2",
                align_items="center",
                flex_shrink="0",
            ),
            connecting_line,
            align_items="center",
            flex=rx.cond(idx < 4, "1", "0"),
            spacing="1",
        )

    desktop_stepper = rx.hstack(
        *[desktop_step_item(i) for i in range(5)],
        width="100%",
        align_items="center",
        justify="between",
        padding_x="0.5em",
    )

    mobile_progress = rx.vstack(
        rx.hstack(
            rx.hstack(
                rx.text(State.t["step_indicator"], size="2", color_scheme="gray"),
                rx.text(f"{State.active_step_number}", size="2", weight="bold", color="cyan"),
                rx.text(State.t["of_indicator"], size="2", color_scheme="gray"),
                rx.text(f"{State.total_active_steps}", size="2", color_scheme="gray"),
                spacing="1",
                align_items="center",
            ),
            rx.spacer(),
            rx.cond(
                State.active_step_name != "",
                rx.box(
                    rx.text(
                        State.active_step_name,
                        color="#00f2fe",
                        size="2",
                        weight="bold",
                        white_space="nowrap",
                        overflow="hidden",
                        text_overflow="ellipsis",
                    ),
                    padding="2px 10px",
                    background="rgba(0, 242, 254, 0.1)",
                    border="1px solid rgba(0, 242, 254, 0.25)",
                    border_radius="999px",
                    max_width={"initial": "160px", "xs": "200px", "sm": "260px"},
                ),
                rx.text("")
            ),
            width="100%",
            align_items="center",
        ),
        rx.progress(
            value=State.step_progress,
            width="100%",
            height="6px",
            color_scheme="cyan",
            aria_label="Overall intake progress",
            border_radius="999px",
        ),
        width="100%",
        spacing="2",
    )

    return rx.box(
        rx.box(mobile_progress, display={"initial": "block", "md": "none"}, width="100%", overflow="hidden"),
        rx.box(desktop_stepper, display={"initial": "none", "md": "flex"}, width="100%", overflow="hidden"),
        padding_bottom="1em",
        width="100%",
        overflow="hidden",
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
                    overflow_x="hidden",
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
    from fastapi import FastAPI, HTTPException
    from pydantic import ValidationError
    from google.api_core.exceptions import GoogleAPIError
    from starlette.responses import Response
    from preconsult.core.errors import (
        RedisUnavailableError,
        RedisQuotaExceededError,
        LLMUnavailableError,
        http_exception_handler,
        redis_unavailable_handler,
        redis_quota_exceeded_handler,
        llm_unavailable_handler,
        validation_handler,
        google_api_handler,
        generic_handler,
    )
    custom_api = FastAPI()
    custom_api.add_exception_handler(RedisUnavailableError, redis_unavailable_handler)
    custom_api.add_exception_handler(RedisQuotaExceededError, redis_quota_exceeded_handler)
    custom_api.add_exception_handler(LLMUnavailableError, llm_unavailable_handler)
    custom_api.add_exception_handler(HTTPException, http_exception_handler)
    custom_api.add_exception_handler(ValidationError, validation_handler)
    custom_api.add_exception_handler(GoogleAPIError, google_api_handler)
    custom_api.add_exception_handler(Exception, generic_handler)
    custom_api.include_router(api_router)
    app._api.mount("/api", custom_api)

    async def health_live(request):
        # Liveness: process is up. No external dependency probed so Cloud Run
        # never restarts a healthy-but-slow-to-warm container unnecessarily.
        from starlette.responses import JSONResponse
        return JSONResponse({"status": "healthy", "checks": {"live": "ok"}})

    async def health_ready(request):
        # Readiness: only serve traffic when Redis is reachable (sessions and
        # rate limiting depend on it). 503 means "don't send me requests yet".
        # Throttled so readiness polling does not burn the serverless Redis quota.
        from starlette.responses import JSONResponse
        redis_status = await check_redis_health_throttled()
        if redis_status != "ok":
            # A distinct code for quota exhaustion so alerts/ops can distinguish
            # "daily quota spent" from a general outage.
            code = "redis_quota_exceeded" if redis_status == "quota_exceeded" else "service_unavailable"
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "redis": redis_status, "code": code},
            )
        return JSONResponse({"status": "ready", "redis": "ok"})

    async def health(request):
        # Aggregate endpoint retained for backward compatibility with the
        # existing CI smoke test which asserts `redis` is "ok"/"unavailable".
        # It also surfaces the Reflex event channel status so ops can confirm
        # the interactive (socket) path works, not just REST/health. Both probes
        # are throttled so frequently-hit health endpoints don't consume the
        # serverless Redis quota.
        from starlette.responses import JSONResponse
        request_id = new_request_id()
        redis_status = await check_redis_health_throttled()
        event_channel = await _throttled_probe("event_channel", probe_event_channel)
        log_event(
            logging.INFO,
            "health.probe",
            request_id=request_id,
            redis=redis_status,
            event_channel=event_channel,
        )
        payload = {
            "status": "healthy",
            "redis": redis_status,
            "event_channel": event_channel,
        }
        # Provide a stable machine-readable code when storage is unhealthy so
        # alerts/CI can key on quota exhaustion as distinct from a general outage.
        if redis_status == "quota_exceeded":
            payload["code"] = "redis_quota_exceeded"
        elif redis_status == "unavailable":
            payload["code"] = "redis_unavailable"
        return JSONResponse(payload)

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
    app._api.add_route("/health/live", health_live, include_in_schema=False, methods=["GET"])
    app._api.add_route("/health/ready", health_ready, include_in_schema=False, methods=["GET"])
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


# Page-level <head> metadata, declared through Reflex's own page machinery
# (add_page(meta=...)) so the server and client render the same <head> and React
# hydration succeeds.
#
# IMPORTANT — only plain <meta> dicts may be returned here. Reflex turns each
# dict into a <meta> tag rendered into <head> on BOTH server and client (safe).
# Generic component entries (rx.el.link / rx.el.script / el.noscript) are
# instead appended to the page <body>, where they are absent from the client
# render and cause React hydration error #418 (the whole app becomes
# un-interactive). Historically hreflang/canonical/JSON-LD/gtag were injected
# into </head> at request time and later added here as components; both break
# hydration. Social-preview and description tags are the safe subset.
def build_index_meta():
    return [
        {"property": "og:image", "content": "https://pre-consult.org/og-image.png"},
        {"property": "og:image:width", "content": "1200"},
        {"property": "og:image:height", "content": "630"},
    ]


app.add_page(
    index,
    on_load=State.detect_lang,
    title="PreConsult — Privacy-First Medical Intake Assistant",
    description="Guided AI interview helper for patient intake with zero data persistence.",
    image="https://pre-consult.org/og-image.png",
    meta=build_index_meta(),
)
app.add_page(
    admin_dashboard,
    route="/admin/dashboard",
    on_load=AdminState.load_analytics,
    title="PreConsult Admin Dashboard",
    description="Analytics funnel dashboard for PreConsult administrators."
)

from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.responses import Response  # noqa: E402

class CustomStaticFiles(StaticFiles):
    # Reflex backend endpoints must never be answered by the SPA fallback. The
    # bare /_event path is handled by an explicit redirect route, but keep this
    # as a defensive backstop so a mis-routed backend request returns a clear
    # 404 text response instead of misleading HTML (which breaks the socket).
    _BACKEND_PREFIXES = (
        "_event",
        "_ping",
        "_health",
        "_upload",
        "auth-codespace",
        "_all_routes",
    )

    async def get_response(self, path: str, scope) -> Response:
        path_lower = path.lower()
        if any(path_lower.endswith(ext) for ext in (".php", ".asp", ".aspx", ".jsp", ".cgi")) or "wp-admin" in path_lower or "wp-content" in path_lower or ".env" in path_lower or "phpmyadmin" in path_lower:
            return Response("Not Found", status_code=404, media_type="text/plain")
        if any(path_lower == prefix or path_lower.startswith(prefix + "/") for prefix in self._BACKEND_PREFIXES):
            # A Reflex backend path reached the SPA fallback. This historically
            # meant the state socket was broken (client got HTML instead of a
            # handshake). Log it so a regression is visible in Cloud Run logs.
            log_event(
                logging.WARNING,
                "static.backend_prefix_404",
                request_id=new_request_id(),
                path=path_lower,
            )
            return Response("Not Found", status_code=404, media_type="text/plain")

        response = await super().get_response(path, scope)

        # The built index.html is Reflex's own SSR output and must be served
        # byte-for-byte so React hydration succeeds. Historically we used to
        # string-inject <head> tags (SEO, og:image, an anti-FOUC <style>, the
        # lang-cookie script, gtag/GTM) into this HTML, but those tags are NOT
        # present in the client render, so React threw hydration error #418 and
        # never attached event handlers (making the whole app un-interactive).
        # SEO + analytics live on the Reflex page via add_page(meta=...) now, so
        # the server HTML and the client render stay identical.
        if "assets/" in path or path.startswith("assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        response.headers["Vary"] = "Accept-Encoding"
        return response

async def probe_event_channel() -> str:
    """Confirm the Reflex event socket (/_event/) answers a handshake.

    Performs an in-process Engine.IO handshake and reports only a status string
    (``ok`` / ``unavailable``). PHI-safe: never returns body content. This is the
    same probe the CI smoke test makes, so /health and CI agree on whether the
    interactive state channel is reachable.
    """
    import httpx
    from httpx import ASGITransport

    try:
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app._api), base_url="http://health"
        ) as client:
            resp = await client.get("/_event/?EIO=4&transport=polling")
        body = resp.content or b""
        if resp.status_code == 200 and body.startswith(b"0"):
            return "ok"
    except Exception:
        pass
    return "unavailable"


# Throttle health probes so frequently-hit health endpoints (CI, scanners, and
# Cloud Run readiness polling) do not consume the serverless Redis quota. Value
# is a TTL window in seconds; statuses are recomputed at most once per window and
# otherwise served from the cache. Requires a worker-global lock to avoid thundering
# herd on cold start.
_health_probe_cache: dict[str, tuple[float, str]] = {}
_health_probe_lock = asyncio.Lock()
_HEALTH_PROBE_TTL_S = 60.0


def _reset_health_probe_cache_unlocked() -> None:
    """Clear the health-probe throttle cache (mainly for deterministic tests)."""
    _health_probe_cache.clear()


async def _throttled_probe(key: str, probe) -> str:
    """Return a cached probe status, refreshing at most once per TTL window.

    ``probe`` is an async callable returning a status string (e.g. ``"ok"``).
    """
    cache_key = f"health:{key}"
    async with _health_probe_lock:
        now = time.monotonic()
        cached = _health_probe_cache.get(cache_key)
        if cached is not None and now - cached[0] < _HEALTH_PROBE_TTL_S:
            return cached[1]
    # Fresh probe outside the lock (still coalesced by the TTL).
    status = await probe()
    async with _health_probe_lock:
        _health_probe_cache[cache_key] = (time.monotonic(), status)
    return status


async def check_redis_health_throttled() -> str:
    """Redis reachability as a throttled status string.

    Returns ``ok`` | ``quota_exceeded`` | ``unavailable`` so an exhausted
    serverless Redis quota is surfaced explicitly rather than as a generic
    outage. Probed at most ~once per minute (see _throttled_probe).
    """
    from preconsult.services.session_service import check_redis_status

    return await _throttled_probe("redis", check_redis_status)


# Reflex mounts the event socket (EngineIO) as a trailing-slash route ``/_event/``
# for the state connection (see reflex's ``_add_socket``), but the browser's
# engine.io polling client requests the **bare** ``/_event`` path. Without the root
# static fallback below, reflex answers that bare path with a 307 redirect to
# ``/_event/`` and the connection succeeds. However the SPA catch-all mounted at
# the end of this router matches ``/_event`` *before* that redirect can apply and
# returns HTML instead of a socket handshake, making "Start Preparing" (and every
# later state change) fail with "cannot connect to server: xhr poll error".
# Re-expose the bare ``/_event`` path explicitly (as reflex already does when no
# static mount is present) so the socket is reachable ahead of the SPA fallback.
def _backend_redirect(request):
    from starlette.responses import RedirectResponse

    query = request.url.query
    location = f"{request.url.path}/" + (f"?{query}" if query else "")
    log_event(
        logging.DEBUG,
        "sock.bare_event_redirect",
        request_id=new_request_id(),
        path=request.url.path,
    )
    return RedirectResponse(url=location, status_code=307)


app._api.add_route("/_event", _backend_redirect, methods=["GET", "POST"])

_STATIC_DIR = os.path.join(os.getcwd(), ".web", "build", "client")
if os.path.exists(_STATIC_DIR):
    app._api.mount("/", CustomStaticFiles(directory=_STATIC_DIR, html=True), name="static")

# Enable application-level Gzip compression for payloads >= 500 bytes (HTML, CSS, JS, API JSON)
app._api.add_middleware(GZipMiddleware, minimum_size=500)


class _RequestIDMiddleware:
    """Stamp an X-Request-ID on every response and emit a PHI-safe request log.

    Only the request method + path are logged (no query string, no headers, no
    body) so nothing user-supplied is captured. The id correlates the request
    across Cloud Run logs and the structured backend events.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = new_request_id()
        scope["request_id"] = request_id
        path = scope.get("path", "")
        log_event(
            logging.DEBUG,
            "http.request",
            request_id=request_id,
            method=scope.get("method", ""),
            path=path if len(path) <= 200 else path[:200],
        )

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                message["headers"] = [
                    *headers,
                    (b"x-request-id", request_id.encode("ascii")),
                ]
            await send(message)

        await self.app(scope, receive, send_with_id)


class _BotGateMiddleware:
    """Block obvious scanners/bots BEFORE they reach Redis-touching endpoints.

    With serverless Redis on a free tier, a scanner burst against /_event,
    /api/session/init or /api/analytics/event can exhaust the request quota that
    real users need. This is a lightweight, conservative gate: it only matches a
    small set of unambiguous CLI/bot user-agents on the Redis-backed paths and
    returns a fast 403 without touching storage. Browser traffic passes through
    untouched (permissive by design); Cloudflare WAF/Bot Shield can be stricter.
    """

    # Only these paths may trigger Redis (sessions, rate-limit, analytics).
    _REDIS_PATHS = (
        "/api/session/init",
        "/api/interview-questions-stream",
        "/api/initial-questions-stream",
        "/api/generate-pdf",
        "/api/analytics/event",
    )
    # Case-insensitive substrings that identify unambiguous non-browser clients.
    _BOT_UA_FRAGMENTS = (
        "curl",
        "wget",
        "python-requests",
        "python-urllib",
        "go-http-client",
        "node-fetch",
        "php/",
        "java/",
        "axios",
        "okhttp",
        "libwww-perl",
        "scrapy",
        "headlesschrome",
        "phantomjs",
        "screaming frog",
        "ahrefsbot",
        "semrushbot",
        "mj12bot",
        "dotbot",
        "bytespider",
        "petalbot",
        "awario",
        "pycurl",
    )

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not any(path.startswith(p) for p in self._REDIS_PATHS):
            await self.app(scope, receive, send)
            return

        user_agent = ""
        for name, value in scope.get("headers", []):
            if name == b"user-agent":
                user_agent = value.decode("latin-1", "replace")
                break

        if user_agent and any(frag in user_agent.lower() for frag in self._BOT_UA_FRAGMENTS):
            # PHI-safe: log a hash of the UA, never the raw value.
            import hashlib
            ua_hash = hashlib.sha256(user_agent.encode("utf-8", "replace")).hexdigest()[:16]
            log_event(
                logging.INFO,
                "gate.blocked",
                request_id=new_request_id(),
                path=path[:200],
                ua_hash=ua_hash,
            )
            await send({
                "type": "http.response.start",
                "status": 403,
                "headers": [(b"content-type", b"text/plain"), (b"content-length", b"9")],
            })
            await send({"type": "http.response.body", "body": b"Forbidden"})
            return

        await self.app(scope, receive, send)


app._api.router.lifespan_context = app._run_lifespan_tasks
api = _BotGateMiddleware(_RequestIDMiddleware(app._context_middleware(app._api)))

