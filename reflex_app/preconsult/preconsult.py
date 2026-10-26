import os
import asyncio
import logging
import time
import reflex as rx
from starlette.middleware.gzip import GZipMiddleware
from .state import State
from preconsult.core.observability import log_event, new_request_id, _inc
from preconsult.api.app import build_api_app
from preconsult.site import health as site_health
from preconsult.site.health import (  # noqa: F401  (re-exported for tests)
    _reset_health_probe_cache_unlocked,
    register_health_routes,
)
from preconsult.site.middleware import BotGateMiddleware
from preconsult.site.routes import register_site_routes
from preconsult.site.static import SPAStaticFiles


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

# --- API + public surface ---------------------------------------------------
# Construction lives in Reflex-free modules so the cutover does not have to
# rewrite them; the host only wires them onto its Starlette app, in the same
# order as before (/api first, then health, then the crawler/legal documents).
custom_api = build_api_app()
app._api.mount("/api", custom_api)
register_health_routes(app._api)
register_site_routes(app._api)

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
            # Content-hashed build artifacts are immutable: once a URL exists it
            # never changes content, so they can be cached at the edge for a year.
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            # HTML *documents* (the shell that references the hashed chunks) MUST
            # be revalidated on every navigation. If index.html is cached while
            # the build advances, the browser resolves stale chunk URLs that 404
            # on the new revision, can't load the app, and falls back to an old
            # socket client — surfacing as "unsupported version of the Socket.IO
            # or Engine.IO protocols" on /_event. Because chunk names are
            # content-hashed, an uncacheable document always points at valid
            # current assets, so this is the single lever that prevents the class
            # of stale-shell breakage seen in production.
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        response.headers["Vary"] = "Accept-Encoding"
        return response

async def probe_event_channel() -> str:
    """Confirm the Reflex event socket is reachable.

    For the ``polling`` transport this performs an in-process Engine.IO HTTP
    handshake and reports ``ok``/``unavailable``. For the ``websocket`` transport
    an in-process HTTP probe cannot complete a real WebSocket upgrade (the engine
    rejects a plain HTTP GET with ``400 Invalid websocket upgrade``), so instead
    we confirm the socket engine is configured to serve ``websocket`` — the actual
    interactive channel is asserted by the browser-based E2E (test_socket_session)
    and the CI smoke test's real client. PHI-safe: only a status string.
    """
    # The event transport is the runtime env var REFLEX_TRANSPORT, the same single
    # source of truth rxconfig.config.transport reads (rxconfig.debug config attr).
    # Read it directly here instead of `from reflex_app import rxconfig`: the
    # container starts with WORKDIR /app/reflex_app (see Dockerfile), so the parent
    # `reflex_app` package is NOT importable and that import raised
    # ModuleNotFoundError, crashing /health with a 500. Default matches rxconfig.
    if os.environ.get("REFLEX_TRANSPORT", "websocket") != "websocket":
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

    # websocket transport: verify the engine advertises the websocket transport.
    try:
        sio = getattr(app, "sio", None)
        if sio is not None:
            transports = getattr(sio, "eio", None).transports
            if "websocket" in transports:
                return "ok"
    except Exception:
        pass
    return "unavailable"


# The health module is Reflex-free and therefore cannot import Reflex. While
# Reflex still owns the Engine.IO socket, the host injects the only
# Reflex-shaped probe it needs; after the cutover nothing sets it and /health
# reports "not_configured" instead of probing a route that no longer exists.
site_health.event_channel_probe = probe_event_channel

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


# --- Shadow SPA at /next ----------------------------------------------------
# The React rewrite (web/) is served from the same image under /next while
# Reflex still owns /. It must be mounted BEFORE the root static catch-all so
# /next/* resolves to the SPA, but it only ever matches the /next prefix, so it
# cannot shadow /api, /_event, or /health. The SPA is a client-side router, so
# any non-file path under /next must fall through to index.html; hashed assets
# are immutable and the document is no-store (mirrors the Reflex shell rules).
_NEXT_DIST = os.environ.get(
    "WEB_DIST_DIR",
    os.path.abspath(os.path.join(os.getcwd(), "..", "web", "dist")),
)
if os.path.exists(_NEXT_DIST):
    app._api.mount("/next", SPAStaticFiles(directory=_NEXT_DIST, html=True), name="spa")

_STATIC_DIR = os.path.join(os.getcwd(), ".web", "build", "client")
if os.path.exists(_STATIC_DIR):
    app._api.mount("/", CustomStaticFiles(directory=_STATIC_DIR, html=True), name="static")

# Enable application-level Gzip compression for payloads >= 500 bytes (HTML, CSS, JS, API JSON)
app._api.add_middleware(GZipMiddleware, minimum_size=500)


# Throttled Sentry event bridge for high-frequency failure tells.
#
# socket.handshake_rejected can fire on every scanner/bot probe and would flood
# Sentry if each occurrence produced a record. We coalesce to at most one per
# TTL window per event-name (mirrors the /health probe throttling), keeping the
# error tracker useful without a quota/bill hit. PHI-safe: only event name,
# path, status and request_id — never user content.
_SENTRY_EVENT_LOCK = asyncio.Lock()
_sentry_last_emit: dict[str, float] = {}
_SENTRY_EMIT_TTL_S = 300.0  # 5 min


def _sentry_throttled_event(event_name: str, **context) -> None:
    """Emit a Sentry error at most once per TTL per event name (throttled)."""
    now = time.monotonic()
    async def _emit():
        global _sentry_last_emit
        async with _SENTRY_EVENT_LOCK:
            if now - _sentry_last_emit.get(event_name, 0.0) < _SENTRY_EMIT_TTL_S:
                return
            _sentry_last_emit[event_name] = now
        try:
            import sentry_sdk
            from sentry_sdk.scope import Scope
            scope = Scope()
            scope.set_extra("event_name", event_name)
            for k, v in context.items():
                scope.set_extra(k, str(v))
            sentry_sdk.capture_message(f"observability.{event_name}", level="warning", scope=scope)
        except Exception:
            pass  # observability must never break the request path

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        loop.create_task(_emit())
    else:
        # No running loop (edge case); run inline best-effort within a fresh loop.
        import asyncio as _asyncio
        try:
            _asyncio.run(_emit())
        except Exception:
            pass


class _StaleSocketSessionMiddleware:
    """Turn a stale-session EngineIO POST into a recoverable 400, not a 500.

    This runs as a Starlette *user* middleware registered on ``app._api`` via
    ``add_middleware``, i.e. it is layered INSIDE reflex's ServerErrorMiddleware.
    That placement matters: python-engineio's unguarded POST branch
    (async_server.py:328) raises ``KeyError('Session is disconnected')`` when a
    browser long-polls an event with a ``sid`` the server has already drained
    (idle ping_timeout, e.g. after a scale-to-zero cold start). If that exception
    escapes, Starlette's ServerErrorMiddleware — which is OUTER to this
    middleware — converts it into an HTTP 500, surfacing in the UI as
    "Cannot connect to server: xhr post error" and freezing the wizard on a
    click such as "Start Preparing".

    Catching here (inner to ServerErrorMiddleware) means the response has not
    been finalized yet, so we can return a clean 400 that the engine.io client
    re-handshakes on. We flag the scope so the outer _RequestIDMiddleware does not
    also attribute this 400 to a protocol mismatch (socket.handshake_rejected);
    a recoverable stale-session is a distinct tell (socket.session_invalid).
    """

    _SCOPE_RECOVERED = "socket.session_recovery"

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except KeyError as exc:
            path = scope.get("path", "")
            method = scope.get("method", "")
            if path.startswith("/_event") and "session" in str(exc).lower():
                scope[self._SCOPE_RECOVERED] = True
                _inc("socket.session_invalid")
                # Extract the engine.io sid from the query string (if present).
                # Random short session id, not user content; PHI-safe. Truncated.
                sid = None
                qs = scope.get("query_string", b"")
                if qs:
                    for part in qs.decode("latin-1", "replace").split("&"):
                        if part.startswith("sid="):
                            sid = part.split("=", 1)[1][-8:]  # tail only
                            break
                log_event(
                    logging.WARNING,
                    "socket.session_invalid",
                    request_id=scope.get("request_id") or new_request_id(),
                    method=method,
                    path=path[:200],
                    reason=str(exc)[:120],
                    sid=sid,
                )
                _sentry_throttled_event(
                    "socket.session_invalid",
                    request_id=scope.get("request_id") or new_request_id(),
                    path=path[:200],
                    method=method,
                    reason=str(exc)[:120],
                )
                # Respond directly so the inner error is not double-sent by
                # ServerErrorMiddleware (which stays "start not sent" because we
                # return normally here).
                body = b"Invalid session"
                await send(
                    {
                        "type": "http.response.start",
                        "status": 400,
                        "headers": [
                            (b"content-type", b"text/plain; charset=UTF-8"),
                            (b"x-request-id", (scope.get("request_id") or new_request_id()).encode("ascii")),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return
            raise


class _RequestIDMiddleware:
    """Stamp an X-Request-ID on every response and emit a PHI-safe request log.

    Only the request method + path are logged (no query string, no headers, no
    body) so nothing user-supplied is captured. The id correlates the request
    across Cloud Run logs and the structured backend events.

    Also captures the response status so the log is alertable by outcome, and
    emits focused WARNING events for the failure classes that produced the
    production socket incident:
      - a rejected Engine.IO handshake (status 400) on ``/_event`` — the
        "unsupported version of the Socket.IO or Engine.IO protocols" symptom of
        a stale-shell/stale-client, even though the origin itself answers EIO=4.
      - a 404 on a static asset under ``/assets`` — the tell that a cached
        index.html shell references chunk URLs that no longer exist.
    These aggregate into "how many users are hitting the stale build" so the
    regression is visible before a user files a bug.
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
        method = scope.get("method", "")
        safe_path = path if len(path) <= 200 else path[:200]
        log_event(
            logging.DEBUG,
            "http.request",
            request_id=request_id,
            method=method,
            path=safe_path,
        )

        status_holder = {}

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                status = message.get("status", 0)
                status_holder["status"] = status
                headers = message.get("headers", [])
                message["headers"] = [
                    *headers,
                    (b"x-request-id", request_id.encode("ascii")),
                ]
                # Correlate a prod/user-facing outcome to a structured event.
                # Only path + status are captured (no query, headers or body),
                # preserving the zero-PHI guarantee.
                if path.startswith("/_event") and status == 400:
                    # A recoverable stale-session 400 is produced (and counted)
                    # by the inner _StaleSocketSessionMiddleware; do not also
                    # misattribute it as a protocol handshake rejection.
                    if not scope.get(_StaleSocketSessionMiddleware._SCOPE_RECOVERED):
                        _inc("socket.handshake_rejected")
                        log_event(
                            logging.WARNING,
                            "socket.handshake_rejected",
                            request_id=request_id,
                            path=safe_path,
                            status=status,
                            reason="engineio_protocol_or_transport",
                        )
                        _sentry_throttled_event(
                            "socket.handshake_rejected",
                            request_id=request_id,
                            path=safe_path,
                            status=status,
                        )
                elif path.startswith("/assets") and status == 404:
                    _inc("static.asset_404")
                    log_event(
                        logging.WARNING,
                        "static.asset_404",
                        request_id=request_id,
                        path=safe_path,
                        status=status,
                    )
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except KeyError:
            # Stale-session recovery is handled by the inner
            # _StaleSocketSessionMiddleware (layered inside ServerErrorMiddleware,
            # where the response has not been finalized yet). By the time an
            # exception reaches this outer layer the ASGI response lifecycle may
            # already be complete, so re-raising (rather than attempting a second
            # send) is the only safe behaviour here.
            raise
        finally:
            status = status_holder.get("status")
            if status is not None:
                _inc(f"http.status.{status}")
                # Surface non-2xx outcomes at INFO so failures are queryable by
                # path+status; 2xx stays at DEBUG to keep log volume modest.
                log_event(
                    logging.INFO if status >= 400 else logging.DEBUG,
                    "http.status",
                    request_id=request_id,
                    method=method,
                    path=safe_path,
                    status=status,
                )


app._api.router.lifespan_context = app._run_lifespan_tasks

# Recover stale Engine.IO sessions as clean 400s instead of 500s. Must be a
# Starlette user middleware on app._api (i.e. INSIDE ServerErrorMiddleware) so
# the KeyError from python-engineio's unguarded POST branch is caught before
# ServerErrorMiddleware finalizes it as an HTTP 500 (the "Cannot connect to
# server: xhr post error" that froze the wizard on "Start Preparing").
app._api.add_middleware(_StaleSocketSessionMiddleware)

api = BotGateMiddleware(_RequestIDMiddleware(app._context_middleware(app._api)))

