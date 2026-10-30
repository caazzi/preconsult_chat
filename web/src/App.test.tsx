import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, beforeEach } from "vitest";

import { App } from "./App";

function renderApp(search = "") {
  window.history.pushState({}, "", `/${search}`);
  return render(<App />);
}

function hero() {
  return within(screen.getByTestId("landing-hero"));
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
      hero().getByRole("button", { name: /start preparing/i }),
    ).toBeInTheDocument();
  });

  it("renders Portuguese when ?lang=pt", () => {
    renderApp("?lang=pt");
    expect(
      hero().getByRole("button", { name: /Começar/i }),
    ).toBeInTheDocument();
  });

  it("keeps the FAQ after the hero in DOM order", () => {
    renderApp("?lang=en");
    const heroSection = screen.getByTestId("landing-hero");
    const faq = screen.getByTestId("faq");

    expect(heroSection.nextElementSibling).toBe(faq);
  });

  it("advances from landing to the first wizard step", async () => {
    const user = userEvent.setup();
    renderApp("?lang=en");
    await user.click(hero().getByRole("button", { name: /start preparing/i }));
    // Stepper appears once the wizard has started.
    expect(
      screen.getByRole("progressbar", { name: /intake progress/i }),
    ).toBeInTheDocument();
  });

  it("renders the landing for an unknown path (stale /next bookmark)", () => {
    renderApp("next/some-old-page?lang=pt");
    expect(
      hero().getByRole("button", { name: /Começar/i }),
    ).toBeInTheDocument();
    // The catch-all redirects to the root and keeps the language query.
    expect(window.location.pathname).toBe("/");
    expect(window.location.search).toBe("?lang=pt");
  });

  it("sets <html lang> on mount for an auto-detected language", () => {
    renderApp("?lang=pt");
    expect(document.documentElement.lang).toBe("pt");
  });

  it("mirrors a language change into the URL without extra storage", async () => {
    const user = userEvent.setup();
    renderApp("?lang=pt");
    await user.selectOptions(
      screen.getByLabelText(/select language/i),
      "en",
    );
    expect(document.documentElement.lang).toBe("en");
    expect(window.location.search).toBe("?lang=en");
    expect(window.localStorage.length).toBe(0);
    expect(document.cookie).toBe("");
  });

  it("points the legal links at the backend pages with the active language", () => {
    renderApp("?lang=pt");
    expect(
      screen.getByRole("link", { name: /política de privacidade/i }),
    ).toHaveAttribute("href", "/privacy?lang=pt");
    expect(
      screen.getByRole("link", { name: /termos de serviço/i }),
    ).toHaveAttribute("href", "/terms?lang=pt");
  });
});
