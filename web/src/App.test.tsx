import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, beforeEach } from "vitest";

import { App } from "./App";

function renderApp(search = "") {
  window.history.pushState({}, "", `/next/${search}`);
  return render(<App />);
}

describe("SPA shell", () => {
  beforeEach(() => {
    document.documentElement.lang = "en";
  });

  it("renders the landing hero and primary CTA", () => {
    renderApp("?lang=en");
    expect(
      screen.getByText(/Prepare for your doctor's appointment/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /start preparing/i }),
    ).toBeInTheDocument();
  });

  it("renders Portuguese when ?lang=pt", () => {
    renderApp("?lang=pt");
    expect(
      screen.getByRole("button", { name: /Começar/i }),
    ).toBeInTheDocument();
  });

  it("advances from landing to the first wizard step", async () => {
    const user = userEvent.setup();
    renderApp("?lang=en");
    await user.click(
      screen.getByRole("button", { name: /start preparing/i }),
    );
    // Stepper appears once the wizard has started.
    expect(
      screen.getByRole("progressbar", { name: /intake progress/i }),
    ).toBeInTheDocument();
  });
});
