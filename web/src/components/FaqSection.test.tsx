import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { App } from "../App";

function renderApp() {
  window.history.pushState({}, "", "/?lang=en");
  return render(<App />);
}

function faq() {
  return within(screen.getByTestId("faq"));
}

describe("landing FAQ", () => {
  beforeEach(() => {
    document.documentElement.lang = "en";
  });

  it("opens the first answer by default", () => {
    renderApp();

    expect(
      faq().getByRole("button", { name: /what is preconsult/i }),
    ).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/privacy-first tool/i)).toBeVisible();
  });

  it("keeps a single answer open at a time", async () => {
    const user = userEvent.setup();
    renderApp();

    const first = faq().getByRole("button", { name: /what is preconsult/i });
    const second = faq().getByRole("button", {
      name: /is my data stored or shared/i,
    });

    await user.click(second);

    expect(first).toHaveAttribute("aria-expanded", "false");
    expect(second).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByRole("region", { name: /is my data stored or shared/i }),
    ).toBeVisible();
    expect(screen.getByText(/privacy-first tool/i)).not.toBeVisible();

    await user.click(second);

    expect(second).toHaveAttribute("aria-expanded", "false");
    expect(
      screen.getByText(/all data is processed temporarily/i),
    ).not.toBeVisible();
  });

  it("starts the wizard from the closing CTA", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(
      faq().getByRole("button", { name: /start preparing/i }),
    );

    expect(
      screen.getByRole("progressbar", { name: /intake progress/i }),
    ).toBeInTheDocument();
  });
});
