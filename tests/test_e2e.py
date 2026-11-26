"""Playwright test — LOCALHOST ONLY (never runs against LinkedIn).
Start the app first:  uvicorn app.main:app --port 8000   (fresh DB)
Run:                  pytest tests/test_e2e.py
Flow: sign up → fill form → lead appears → same post again is rejected as duplicate."""
import os
import uuid

from playwright.sync_api import expect, sync_playwright

BASE = os.getenv("TEST_BASE_URL", "http://localhost:8000")
assert "localhost" in BASE or "127.0.0.1" in BASE, "E2E tests run only against localhost"


def test_add_lead_and_block_duplicate():
    email = f"qa-{uuid.uuid4().hex[:6]}@example.com"
    post_id = str(7399000000000000000 + uuid.uuid4().int % 10**12)
    url = f"https://www.linkedin.com/feed/update/urn:li:activity:{post_id}/"
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(BASE + "/#/signup")
        if pg.locator("[name=name]").count() == 0:
            pg.goto(BASE + "/#/signup")
        pg.fill("[name=name]", "QA Tester")
        pg.fill("[name=email]", email)
        pg.fill("[name=password]", "password123")
        pg.click("button[type=submit]")
        pg.locator(".topbar").or_(pg.get_by_text("Waiting for approval")).first.wait_for()
        if pg.locator("text=Waiting for approval").count():
            b.close()
            raise AssertionError("Run against a fresh database so the test user becomes admin")
        pg.goto(BASE + "/#/add")
        pg.fill("[name=post_url]", url)
        pg.fill("[name=post_text]", "Looking for a performance marketing agency for CPL campaigns. GEO: India")
        pg.fill("[name=author_name]", "Sample Author")
        expect(pg.locator("#detect")).to_contain_text("performance marketing")
        pg.click("#add-submit")
        expect(pg.locator(".drawer")).to_contain_text("Sample Author")
        pg.goto(BASE + "/#/leads/all")
        expect(pg.locator("#feed")).to_contain_text("Sample Author")
        # duplicate
        pg.goto(BASE + "/#/add")
        pg.fill("[name=post_url]", url.replace("feed/update/urn:li:activity:", "posts/someone-activity-"))
        pg.fill("[name=post_text]", "Looking for a performance marketing agency")
        pg.click("#add-submit")
        expect(pg.locator("#add-msg")).to_contain_text("Duplicate")
        b.close()
