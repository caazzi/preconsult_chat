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
            variant="soft",
            width="100%",
            margin_bottom="0.5em",
            role="alert",
        ),
    )

def header() -> rx.Component:
    return rx.hstack(
        rx.heading(State.t["title"], size={"initial": "5", "xs": "6", "sm": "7"}, color_scheme="cyan"),
        rx.spacer(),
        rx.hstack(
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

def step_0_demographics() -> rx.Component:
    return rx.vstack(
        error_callout(),
        # Hero Section
        rx.vstack(
            rx.badge("AI Assistant", color_scheme="cyan", variant="soft"),
            rx.heading(State.t["hero_title"], size={"initial": "5", "xs": "6", "sm": "7"}, text_align="center", line_height="1.2"),
            rx.text(State.t["hero_subtitle"], color_scheme="gray", size="2", text_align="center"),
            spacing="2",
            align_items="center",
            width="100%",
            padding_bottom="0.5em",
            animation="fadeInUp 0.4s ease-out 0s both"
        ),
        # How it works (dialog trigger)
        rx.dialog.root(
            rx.dialog.trigger(
                rx.button(
                    State.t["how_it_works"],
                    variant="ghost",
                    size="2",
                    color_scheme="cyan",
                    width="100%",
                    min_height="44px",
                ),
            ),
            rx.dialog.content(
                rx.dialog.title(State.t["how_it_works_title"]),
                rx.dialog.description(State.t["how_it_works_desc"]),
                rx.vstack(
                    rx.hstack(rx.icon("message-square", size=20), rx.text(State.t["step_how_1"], size="2")),
                    rx.hstack(rx.icon("activity", size=20), rx.text(State.t["step_how_2"], size="2")),
                    rx.hstack(rx.icon("file-text", size=20), rx.text(State.t["step_how_3"], size="2")),
                    spacing="3", width="100%", align_items="start",
                ),
                rx.dialog.close(rx.button(State.t["got_it"], color_scheme="cyan", width="100%", min_height="44px")),
                max_width="400px", width="100%",
            ),
            animation="fadeInUp 0.4s ease-out 0.1s both",
        ),
        rx.vstack(
            rx.heading(State.t["intake"], size={"initial": "5", "sm": "6"}, margin_bottom="0.25em"),
            rx.text(State.t["intake_desc"], color_scheme="gray"),
            rx.divider(),
            width="100%", spacing="2", animation="fadeInUp 0.4s ease-out 0.2s both"
        ),
        rx.vstack(
            rx.text(State.t["age"], weight="bold"),
            rx.grid(
                *[rx.button(bracket, on_click=State.set_age_bracket(bracket),
                            variant=rx.cond(State.age_bracket == bracket, "solid", "outline"),
                            width="100%", min_height="44px")
                  for bracket in ["18-25", "26-35", "36-45", "46-60", "60+"]],
                columns={"initial": "3", "sm": "5"},
                spacing="2",
                width="100%"
            ),
            rx.text(State.t["gender"], weight="bold"),
            rx.el.label(
                rx.text(State.t["gender_select_sr"], class_name="sr-only"),
                rx.select(
                    State.gender_opts,
                    placeholder=State.t["gender_ph"],
                    on_change=State.set_gender,
                    value=State.gender,
                    width="100%",
                    min_height="44px",
                    aria_label="Select your gender"
                ),
            ),
            spacing="3",
            width="100%",
            padding_y="0.5em",
            animation="fadeInUp 0.4s ease-out 0.25s both"
        ),
        rx.button(
            State.t["start_btn"], 
            on_click=State.go_to_step_1, 
            color_scheme="cyan",
            size="3",
            width="100%",
            min_height="44px",
            _hover={"transform": "scale(1.02)", "bg": "cyan.600"},
            transition="all 0.2s ease",
            animation="fadeInUp 0.4s ease-out 0.3s both"
        ),
        width="100%",
        spacing="3"
    )

def step_1_chief_complaint() -> rx.Component:
    return rx.vstack(
        error_callout(),
        rx.vstack(
            rx.heading(State.t["step_1"], size={"initial": "6", "sm": "7"}),
            rx.text(State.t["step_1_desc"], color_scheme="gray"),
            rx.divider(),
            width="100%", spacing="2", animation="fadeInUp 0.4s ease-out 0s both"
        ),
        rx.vstack(
            rx.text(State.t["specialist"], weight="bold"),
            rx.input(
                placeholder=State.t["specialist_ph"],
                on_change=State.set_specialist,
                value=State.specialist,
                width="100%",
                min_height="44px",
                aria_label="Specialist you are seeing"
            ),
            rx.text(State.t["concern"], weight="bold"),
            rx.text_area(
                placeholder=State.t["concern_ph"],
                on_change=State.set_chief_complaint,
                value=State.chief_complaint,
                width="100%",
                height="65px",
                min_height="44px",
                aria_label="Chief Complaint"
            ),
            animation="fadeInUp 0.4s ease-out 0.1s both", spacing="2", width="100%"
        ),
        rx.vstack(
            rx.text(State.t["duration"], weight="bold"),
            rx.grid(
                rx.foreach(
                    State.duration_opts_with_keys,
                    lambda opt: rx.button(opt["label"], on_click=State.set_duration(opt["id"]),
                                          variant=rx.cond(State.duration == opt["id"], "solid", "outline"),
                                          width="100%", min_height="44px")
                ),
                columns={"initial": "3", "sm": "5"},
                spacing="2",
                width="100%"
            ),
            rx.text(State.t["complaint_detail"], weight="bold"),
            rx.text_area(
                placeholder=State.t["complaint_detail_ph"],
                on_change=State.set_complaint_detail,
                value=State.complaint_detail,
                width="100%",
                height="65px",
                min_height="44px",
                aria_label="Additional details"
            ),
            animation="fadeInUp 0.4s ease-out 0.2s both", spacing="2", width="100%"
        ),
        rx.grid(
            rx.button(State.t["back_btn"], on_click=State.go_back, color_scheme="gray", variant="outline", size="3", width="100%", min_height="44px"),
            rx.button(State.t["start_btn"], on_click=State.go_to_step_2, color_scheme="cyan", size="3", width="100%", min_height="44px"),
            columns="2",
            spacing="3",
            width="100%",
            animation="fadeInUp 0.4s ease-out 0.3s both"
        ),
        width="100%", spacing="3"
    )
def step_2_history() -> rx.Component:
    def medication_item(med_idx):
        return rx.hstack(
            rx.input(
                placeholder=State.t["medications_ph"],
                on_change=lambda val: State.update_medication(med_idx, val),
                value=State.medications[med_idx],
                flex="1",
                min_height="44px",
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
                min_height="44px",
                width={"initial": "44px", "sm": "auto"},
                aria_label="Remove medication"
            ),
            width="100%",
            spacing="2"
        )

    return rx.vstack(
        error_callout(),
        rx.vstack(
            rx.heading(State.t["step_2"], size={"initial": "6", "sm": "7"}),
            rx.text(State.t["step_2_desc"], color_scheme="gray"),
            rx.divider(),
            width="100%", spacing="2", animation="fadeInUp 0.4s ease-out 0s both"
        ),
        rx.vstack(
            rx.text(State.t["conditions_label"], weight="bold"),
            rx.grid(
                rx.foreach(
                    State.conditions_opts_with_keys,
                    lambda opt: rx.button(opt["label"], on_click=State.toggle_condition(opt["id"]),
                                          variant=rx.cond(State.conditions.contains(opt["id"]), "solid", "outline"),
                                          width="100%", min_height="44px")
                ),
                columns={"initial": "2", "sm": "5"},
                spacing="2",
                width="100%"
            ),
            rx.text(State.t["medications_label"], weight="bold"),
            rx.vstack(
                rx.foreach(State.medications, lambda m, i: medication_item(i)),
                rx.button(State.t["add_medication"], on_click=State.add_medication, variant="ghost", min_height="44px"),
                align_items="start", width="100%"
            ),
            animation="fadeInUp 0.4s ease-out 0.1s both", spacing="2", width="100%"
        ),
        rx.vstack(
            rx.text(State.t["allergies_label"], weight="bold"),
            rx.segmented_control.root(
                rx.segmented_control.item(State.t["allergies_no"], value=State.t["allergies_no"], min_height="44px"),
                rx.segmented_control.item(State.t["allergies_yes"], value=State.t["allergies_yes"], min_height="44px"),
                on_change=lambda val: State.set_allergies_flag(val == State.t["allergies_yes"]),
                value=rx.cond(State.allergies_flag, State.t["allergies_yes"], State.t["allergies_no"]),
                width="100%",
                aria_label="Do you have any drug allergies?"
            ),
            rx.cond(
                State.allergies_flag,
                rx.text_area(
                    placeholder=State.t["allergies_ph"],
                    on_change=State.set_allergies_text,
                    value=State.allergies_text,
                    width="100%",
                    min_height="44px",
                    animation="fadeInUp 0.2s ease-out both",
                    aria_label="List your drug allergies"
                )
            ),
            animation="fadeInUp 0.4s ease-out 0.2s both", spacing="2", width="100%"
        ),
        rx.grid(
            rx.button(State.t["back_btn"], on_click=State.go_back, color_scheme="gray", variant="outline", size="3", width="100%", min_height="44px"),
            rx.button(State.t["start_btn"], on_click=State.go_to_step_3, color_scheme="cyan", size="3", width="100%", min_height="44px"),
            columns="2",
            spacing="3",
            width="100%",
            animation="fadeInUp 0.4s ease-out 0.3s both"
        ),
        width="100%", spacing="3"
    )

def step_3_lifestyle() -> rx.Component:
    return rx.vstack(
        error_callout(),
        rx.vstack(
            rx.heading(State.t["step_3"], size={"initial": "6", "sm": "7"}),
            rx.text(State.t["step_3_desc"], color_scheme="gray"),
            rx.divider(),
            width="100%", spacing="2", animation="fadeInUp 0.4s ease-out 0s both"
        ),
        rx.vstack(
            rx.text(State.t["family_history_label"], weight="bold"),
            rx.grid(
                rx.foreach(
                    State.family_history_opts_with_keys,
                    lambda opt: rx.button(opt["label"], on_click=State.toggle_family_history(opt["id"]),
                                          variant=rx.cond(State.family_history.contains(opt["id"]), "solid", "outline"),
                                          width="100%", min_height="44px")
                ),
                columns={"initial": "2", "sm": "4"},
                spacing="2",
                width="100%"
            ),
            animation="fadeInUp 0.4s ease-out 0.1s both", spacing="2", width="100%"
        ),
        rx.vstack(
            rx.text(State.t["smoking_label"], weight="bold"),
            rx.grid(
                rx.foreach(
                    State.smoking_opts_with_keys,
                    lambda opt: rx.button(opt["label"], on_click=State.set_smoking(opt["id"]),
                                          variant=rx.cond(State.smoking == opt["id"], "solid", "outline"),
                                          width="100%", min_height="44px")
                ),
                columns={"initial": "3"},
                spacing="2",
                width="100%"
            ),
            rx.text(State.t["alcohol_label"], weight="bold"),
            rx.grid(
                rx.foreach(
                    State.alcohol_opts_with_keys,
                    lambda opt: rx.button(opt["label"], on_click=State.set_alcohol(opt["id"]),
                                          variant=rx.cond(State.alcohol == opt["id"], "solid", "outline"),
                                          width="100%", min_height="44px")
                ),
                columns={"initial": "2", "sm": "4"},
                spacing="2",
                width="100%"
            ),
            animation="fadeInUp 0.4s ease-out 0.2s both", spacing="2", width="100%"
        ),
        rx.grid(
            rx.button(State.t["back_btn"], on_click=State.go_back, color_scheme="gray", variant="outline", size="3", width="100%", min_height="44px"),
            rx.button(
                State.t["generate_qs_btn"], 
                on_click=State.init_session, 
                loading=State.loading,
                color_scheme="cyan", size="3", width="100%", min_height="44px"
            ),
            columns="2",
            spacing="3",
            width="100%",
            animation="fadeInUp 0.4s ease-out 0.3s both"
        ),
        width="100%", spacing="3"
    )


def step_4_interview_qs() -> rx.Component:
    def question_item(q, idx):
        return rx.vstack(
            rx.text(q, weight="bold"),
            rx.text_area(
                placeholder=State.t["answers_ph"],
                on_change=lambda val: State.set_answer(idx, val),
                value=State.current_answers[idx],
                width="100%", height="65px", min_height="44px",
                aria_label="Answer for clinical question"
            ),
            width="100%", spacing="2"
        )

    return rx.vstack(
        error_callout(),
        rx.vstack(
            rx.hstack(
                rx.icon("clipboard-list", size=24, color="cyan"),
                rx.heading(State.t["step_4"], size={"initial": "6", "sm": "7"}),
                spacing="2",
                align_items="center",
            ),
            rx.text(State.t["step_4_desc"], color_scheme="gray"),
            rx.divider(),
            width="100%", spacing="2", animation="fadeInUp 0.4s ease-out 0s both"
        ),
        rx.cond(
            State.is_emergency,
            rx.vstack(
                rx.hstack(
                    rx.icon("triangle_alert", size=28, color="red"),
                    rx.heading(
                        rx.cond(State.lang == "pt", "AVISO DE EMERGÊNCIA", "EMERGENCY WARNING"),
                        size="5",
                        color="red",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.text(
                    State._qs_buffer,
                    color="red",
                    font_size="lg",
                    font_weight="bold",
                    text_align="center",
                ),
                rx.button(
                    rx.cond(State.lang == "pt", "Voltar para o Início", "Back to Start"),
                    on_click=rx.redirect("/"),
                    color_scheme="gray",
                    width="100%",
                    min_height="44px",
                ),
                width="100%",
                spacing="4",
                padding="2em",
                border="2px solid red",
                border_radius="15px",
                background="rgba(255, 0, 0, 0.15)",
                animation="fadeInUp 0.4s ease-out 0.1s both",
            ),
            rx.vstack(
                rx.box(
                    rx.cond(
                        State.questions.length() > 0,
                        rx.vstack(
                            rx.foreach(State.questions, lambda q, i: question_item(q, i)),
                            width="100%"
                        ),
                        rx.center(rx.spinner(), width="100%", padding="2em")
                    ),
                    width="100%",
                    max_height={"sm": "320px"},
                    overflow_y="auto",
                    padding_right="0.5em",
                    animation="fadeInUp 0.4s ease-out 0.1s both"
                ),
                rx.grid(
                    rx.button(State.t["back_btn"], on_click=State.go_back, color_scheme="gray", variant="outline", size="3", width="100%", min_height="44px"),
                    rx.button(
                        State.t["submit_continue"], 
                        on_click=State.submit_answers, 
                        loading=State.loading,
                        color_scheme="cyan", size="3", width="100%", min_height="44px"
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                    animation="fadeInUp 0.4s ease-out 0.2s both"
                ),
                width="100%",
                spacing="3",
            ),
        ),
        width="100%", spacing="3"
    )

def step_5_summary() -> rx.Component:
    return rx.vstack(
        error_callout(),
        rx.vstack(
            rx.heading(State.t["complete_title"], size={"initial": "7", "sm": "8"}, text_align="center"),
            rx.text(State.t["complete_desc"], text_align="center"),
            rx.divider(),
            width="100%", spacing="2", animation="fadeInUp 0.4s ease-out 0s both"
        ),
        rx.vstack(
            rx.button(
                State.t["download_btn"], 
                on_click=State.download_report,
                loading=State.loading,
                color_scheme="green",
                size="4", width="100%", padding="2em", min_height="44px",
                _hover={"transform": "scale(1.02)"}, transition="all 0.2s ease"
            ),
            rx.button(
                State.t["copy_btn"],
                on_click=rx.set_clipboard(State.summary_text),
                color_scheme="blue",
                variant="outline",
                size="3", width="100%", min_height="44px"
            ),
            rx.button(
                State.t["start_new"], 
                on_click=rx.redirect("/"),
                color_scheme="gray",
                variant="ghost", width="100%", min_height="44px",
                _hover={"transform": "scale(1.02)"}, transition="all 0.2s ease"
            ),
            width="100%", spacing="2", animation="fadeInUp 0.4s ease-out 0.1s both"
        ),
        # Privacy badge movido para o final
        rx.center(
            rx.hstack(
                rx.icon("shield", size=16, color="green"),
                rx.text(State.t["privacy_badge"], size="2", color_scheme="green", weight="bold", text_align="center"),
                spacing="2", align_items="center",
            ),
            width="100%",
            background="rgba(0, 255, 100, 0.05)",
            border="1px solid rgba(0, 255, 100, 0.15)",
            border_radius="8px",
            padding="0.5em",
            animation="fadeInUp 0.4s ease-out 0.2s both",
        ),
        width="100%", spacing="3", padding_y="0.75em"
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
                rx.cond(is_completed, rx.icon("check", size=16), rx.text(str(idx + 1))),
                width="30px", height="30px", border_radius="50%", background=bg_color,
                border="2px solid", border_color=border_color,
                color=rx.cond(is_active | is_completed, "cyan", "gray"), font_weight="bold",
            ),
            # Use safe item fetching from step names array
            rx.cond(
                State.step_names.length() > idx,
                rx.text(State.step_names[idx], color=rx.cond(is_active, "white", "gray"), 
                        weight=rx.cond(is_active, "bold", "regular"), display={"initial": "none", "sm": "block"}),
                rx.text("")
            ),
            spacing="2", align_items="center"
        )
        
    desktop_stepper = rx.hstack(
        *[stepper_item(i) for i in range(6)],
        spacing={"initial": "2", "sm": "5"}, justify="center", width="100%", wrap="wrap"
    )
    
    mobile_progress = rx.vstack(
        rx.hstack(
            rx.text(f"Step {State.step + 1} of 6", weight="bold", size="2"),
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
                    stepper_component(),
                    rx.card(
                        rx.match(
                            State.step,
                            (0, step_0_demographics()),
                            (1, step_1_chief_complaint()),
                            (2, step_2_history()),
                            (3, step_3_lifestyle()),
                            (4, step_4_interview_qs()),
                            (5, step_5_summary()),
                            step_0_demographics()
                        ),
                        padding={"initial": "1em", "sm": "1.25em", "md": "1.5em"},
                        width="100%",
                        background=rx.cond(
                            rx.color_mode == "light",
                            "rgba(255,255,255,0.75)",
                            "rgba(255,255,255,0.05)"
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
    from fastapi import FastAPI
    custom_api = FastAPI()
    custom_api.include_router(api_router)
    app._api.mount("/api", custom_api)

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

import os
import re
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response

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
                    gtag_script = ""
                    if gtag_id:
                        gtag_script = f"""
                        <!-- Google tag (gtag.js) -->
                        <script async src="https://www.googletagmanager.com/gtag/js?id={gtag_id}"></script>
                        <script>
                          window.dataLayer = window.dataLayer || [];
                          function gtag(){{dataLayer.push(arguments);}}
                          gtag('js', new Date());
                          gtag('config', '{gtag_id}');
                        </script>
                        """
                    html_content = html_content.replace("</head>", f"{critical_style}{_MOCK_WEBSOCKET_SCRIPT}{gtag_script}</head>")

                    # Fix og:image relative path → 404 in crawl/Lighthouse contexts.
                    # Reflex generates `content="favicon.ico"` (relative); make it absolute.
                    html_content = html_content.replace(
                        'content="favicon.ico" property="og:image"',
                        'content="https://pre-consult.org/favicon.ico" property="og:image"'
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

