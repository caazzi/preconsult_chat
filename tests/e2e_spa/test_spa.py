"""SPA E2E: the React app end-to-end at ``/`` with a mocked API.

These specs drive the real built SPA (web/dist) served by the real backend at
``/``, but intercept ``/api`` at the browser layer so no live provider or
serverless Redis is needed. They assert the SPA boots, carries the production
head, walks the wizard and writes no client storage.
"""

import json

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e


def _mock_api(page):
    def handler(route):
        url = route.request.url
        if url.endswith("/api/session/init"):
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"session_id": "spa-e2e-session"}),
            )
        elif url.endswith("/api/interview-questions-stream"):
            body = (
                'data: "1. Do you have fever?\\n2. Any pain?\\n"\n\n'
                'data: {"type":"questions","questions":["Do you have fever?","Any pain?"]}\n\n'
            )
            route.fulfill(
                status=200,
                content_type="text/event-stream",
                body=body,
            )
        elif url.endswith("/api/analytics/event"):
            route.fulfill(status=200, content_type="application/json", body="{}")
        else:
            route.continue_()

    page.route("**/api/**", handler)


def test_spa_boots_at_root(page, backend):
    page.goto(f"{backend}/", wait_until="networkidle")
    # Landing hero is rendered by the SPA.
    hero = page.get_by_test_id("landing-hero")
    assert hero.get_by_role("button", name="Start Preparing").is_visible()
    # The document is the canonical one now: indexable, with real social tags.
    robots = page.locator('meta[name="robots"]')
    assert robots.count() == 0 or "noindex" not in (robots.get_attribute("content") or "")
    assert "PreConsult" in page.title()
    assert page.locator('meta[property="og:image"]').count() == 1


def test_faq_is_below_the_hero(page, backend):
    """Regression guard for the row-flex bug that put the FAQ beside the hero."""
    for width, height in ((1280, 900), (375, 667)):
        page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{backend}/", wait_until="networkidle")

        hero = page.get_by_test_id("landing-hero")
        faq = page.get_by_test_id("faq")
        hero_box = hero.bounding_box()
        faq_box = faq.bounding_box()
        assert hero_box and faq_box

        assert faq_box["y"] >= hero_box["y"] + hero_box["height"] - 1
        assert (
            abs(
                (faq_box["x"] + faq_box["width"] / 2)
                - (hero_box["x"] + hero_box["width"] / 2)
            )
            < 2
        )


def test_landing_is_crawlable_without_javascript(browser, backend):
    """The served document carries the landing before any JS runs.

    `sitemap.xml` and `llms.txt` point at `/`, so what a crawler — or a visitor
    with JavaScript disabled — receives must not be an empty `#root`. Each
    language has its own prerendered document.
    """
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    try:
        page.goto(f"{backend}/", wait_until="domcontentloaded")
        assert "Prepare for your doctor" in page.get_by_role(
            "heading", level=1
        ).inner_text()
        assert page.get_by_role(
            "heading", name="Frequently Asked Questions"
        ).is_visible()
        assert page.get_by_text("What is PreConsult?", exact=True).is_visible()
        assert page.locator("html").get_attribute("lang") == "en"

        # The pt URL is a real crawler document, not the English shell with a
        # client-side language switch.
        page.goto(f"{backend}/?lang=pt", wait_until="domcontentloaded")
        assert "Prepare-se" in page.get_by_role("heading", level=1).inner_text()
        assert page.locator("html").get_attribute("lang") == "pt"
    finally:
        context.close()


def test_spa_has_no_localstorage_phi(page, backend):
    page.goto(f"{backend}/", wait_until="networkidle")
    # Zero-PHI: no localStorage/sessionStorage keys should be created.
    ls = page.evaluate("() => Object.keys(window.localStorage)")
    ss = page.evaluate("() => Object.keys(window.sessionStorage)")
    assert ls == []
    assert ss == []


def test_spa_wizard_flow(page, backend):
    _mock_api(page)
    page.goto(f"{backend}/?lang=en", wait_until="networkidle")

    page.get_by_test_id("landing-hero").get_by_role(
        "button", name="Start Preparing"
    ).click()
    page.get_by_role("button", name="26-35").click()
    page.get_by_label("Select your gender").select_option("Female")
    page.get_by_role("button", name="Continue").click()

    page.get_by_label("Chief Complaint").fill("chest pain")
    page.get_by_role("button", name="Weeks").click()
    page.get_by_label("Specialist you are seeing").fill("Cardiologist")
    page.get_by_role("button", name="Continue").click()

    # Medical history step
    page.get_by_role("button", name="Diabetes").click()
    page.get_by_role("button", name="Continue").click()

    # Lifestyle step -> create session & stream questions (mocked)
    page.get_by_role("button", name="Generate My Questions").click()

    # The streamed questions render as answer fields.
    expect(page.get_by_text("Do you have fever?")).to_be_visible(timeout=10000)
    answers = page.get_by_label("Answer for this question")
    expect(answers.first).to_be_visible()

    # A patient who does not know can say so instead of inventing an answer.
    page.get_by_role("button", name="I don't know").first.click()
    expect(answers.first).to_have_value("I don't know")

    # Every question is answered, so the summary is generated and ready.
    page.get_by_role("button", name="I don't know").nth(1).click()
    page.get_by_role("button", name="Generate My Summary").click()
    expect(page.get_by_text("Report Ready")).to_be_visible()
