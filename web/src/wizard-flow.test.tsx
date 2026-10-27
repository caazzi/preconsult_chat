import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const QUESTIONS = ["Do you have fever?", "Any pain?"];

/** Mock the whole session lifecycle: init, the SSE stream, analytics. */
function mockApi(streamBody?: string) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("/api/session/init")) {
      return new Response(JSON.stringify({ session_id: "sess-test" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("/api/interview-questions-stream")) {
      const body =
        streamBody ??
        'data: "1. Do you have fever?\\n2. Any pain?"\n\n' +
          `data: ${JSON.stringify({ type: "questions", questions: QUESTIONS })}\n\n`;
      return new Response(body, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      });
    }
    // analytics + anything else
    return new Response("{}", { status: 200 });
  });
}

async function startIntake(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /start preparing/i }));
}

/** Steps 1-2, leaving the wizard on Step 3 (medical history). */
async function fillDemographicsAndComplaint(
  user: ReturnType<typeof userEvent.setup>,
) {
  // Step 1: choose an age bracket and a gender
  await user.click(screen.getByRole("button", { name: "26-35" }));
  await user.selectOptions(screen.getByLabelText(/select your gender/i), "Female");
  await user.click(screen.getByRole("button", { name: /^continue$/i }));
  // Step 2: chief complaint + specialist
  await user.type(screen.getByLabelText(/chief complaint/i), "chest pain");
  await user.click(screen.getByRole("button", { name: /^weeks$/i }));
  await user.type(
    screen.getByLabelText(/specialist you are seeing/i),
    "Cardiologist",
  );
  await user.click(screen.getByRole("button", { name: /^continue$/i }));
}

async function advanceToHistory(user: ReturnType<typeof userEvent.setup>) {
  await startIntake(user);
  await fillDemographicsAndComplaint(user);
}

/** From Step 3: submit lifestyle and create the session. */
async function submitLifestyle(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /^continue$/i }));
  await user.click(
    screen.getByRole("button", { name: /generate my questions/i }),
  );
}

/** As above, then await the streamed question list. */
async function generateQuestions(user: ReturnType<typeof userEvent.setup>) {
  await submitLifestyle(user);
  await screen.findByText(QUESTIONS[0]);
}

async function advanceToQuestions(user: ReturnType<typeof userEvent.setup>) {
  await advanceToHistory(user);
  await generateQuestions(user);
}

describe("wizard flow (mocked backend)", () => {
  afterEach(() => vi.restoreAllMocks());

  it("walks demographics -> complaint -> history and creates a session", async () => {
    const fetchSpy = mockApi();
    const user = userEvent.setup();
    window.history.pushState({}, "", "/?lang=en");
    render(<App />);

    await advanceToHistory(user);
    expect(
      screen.getByRole("heading", { name: /Medical History/i }),
    ).toBeInTheDocument();

    // Step 3 -> Step 4 (lifestyle)
    await user.click(screen.getByRole("button", { name: /^continue$/i }));
    expect(
      screen.getByRole("heading", { name: /Lifestyle/i }),
    ).toBeInTheDocument();

    // Step 4 -> create session (mocked)
    await user.click(
      screen.getByRole("button", { name: /generate my questions/i }),
    );
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/session/init"),
        expect.objectContaining({ credentials: "include", method: "POST" }),
      );
    });
  });

  it("lets the patient say they don't know instead of inventing an answer", async () => {
    mockApi();
    const user = userEvent.setup();
    window.history.pushState({}, "", "/?lang=en");
    render(<App />);

    await advanceToQuestions(user);

    const unknown = screen.getAllByRole("button", { name: /^i don't know$/i });
    expect(unknown).toHaveLength(QUESTIONS.length);
    for (const button of unknown) await user.click(button);

    expect(unknown[0]).toHaveAttribute("aria-pressed", "true");
    const fields = screen.getAllByLabelText(/answer for this question/i);
    expect((fields[0] as HTMLTextAreaElement).value).toBe("I don't know");
    expect((fields[1] as HTMLTextAreaElement).value).toBe("I don't know");

    await user.click(
      screen.getByRole("button", { name: /generate my summary/i }),
    );

    // No validation error: an explicit "I don't know" is a valid answer.
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /report ready/i }),
    ).toBeInTheDocument();
  });

  it("still asks for an answer when a question is left blank", async () => {
    mockApi();
    const user = userEvent.setup();
    window.history.pushState({}, "", "/?lang=en");
    render(<App />);

    await advanceToQuestions(user);
    await user.click(
      screen.getByRole("button", { name: /generate my summary/i }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/answer every question/i);
  });

  it("confirms before an accidental reload once the intake has started", async () => {
    mockApi();
    const user = userEvent.setup();
    window.history.pushState({}, "", "/?lang=en");
    render(<App />);

    const onLanding = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(onLanding);
    expect(onLanding.defaultPrevented).toBe(false);

    await user.click(screen.getByRole("button", { name: /start preparing/i }));

    const inFlow = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(inFlow);
    expect(inFlow.defaultPrevented).toBe(true);
  });

  it("does not nag before leaving the emergency warning", async () => {
    mockApi(`data: ${JSON.stringify("1. EMERGENCY: call 911 now")}\n\n`);
    const user = userEvent.setup();
    window.history.pushState({}, "", "/?lang=en");
    render(<App />);

    await advanceToHistory(user);
    await submitLifestyle(user);
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();

    // An emergency is the one exit that must never be blocked by a confirm.
    const leaving = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(leaving);
    expect(leaving.defaultPrevented).toBe(false);
  });

  it("moves focus to the new step and labels the regenerate button", async () => {
    mockApi();
    const user = userEvent.setup();
    window.history.pushState({}, "", "/?lang=en");
    render(<App />);

    await startIntake(user);
    expect(document.activeElement?.getAttribute("tabindex")).toBe("-1");
    expect(document.activeElement?.textContent).toContain("Patient Intake");

    await fillDemographicsAndComplaint(user);
    expect(document.activeElement?.textContent).toContain("Medical History");

    await generateQuestions(user);
    expect(
      screen.getByRole("button", { name: /ask different questions/i }),
    ).toBeInTheDocument();
  });
});
