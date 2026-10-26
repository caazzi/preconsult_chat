import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

function mockSessionInit() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("/api/session/init")) {
      return new Response(JSON.stringify({ session_id: "sess-test" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    // analytics + anything else
    return new Response("{}", { status: 200 });
  });
}

async function advanceToHistory(user: ReturnType<typeof userEvent.setup>) {
  // Landing -> Step 1
  await user.click(screen.getByRole("button", { name: /start preparing/i }));
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
  // Now on Step 3 (medical history)
}

describe("wizard flow (mocked backend)", () => {
  afterEach(() => vi.restoreAllMocks());

  it("walks demographics -> complaint -> history and creates a session", async () => {
    const fetchSpy = mockSessionInit();
    const user = userEvent.setup();
    window.history.pushState({}, "", "/next/?lang=en");
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
});
