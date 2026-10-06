"""
Captures website screenshots for the report (app must be running on :5000).
    python take_screenshots.py
Uses the installed Microsoft Edge through Playwright. Re-run `python seed.py` afterwards,
because the screenshots add searches and views to the demo data.
"""
import os

from playwright.sync_api import sync_playwright

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
BASE = "http://127.0.0.1:5000"


def login(page, email, pw):
    page.goto(f"{BASE}/logout")
    page.goto(f"{BASE}/login")
    page.fill("#email", email)
    page.fill("#password", pw)
    page.click("form button.btn-block")
    page.wait_for_load_state("networkidle")


def shot(page, name, height=None, clip_selector=None):
    page.evaluate("document.querySelectorAll('main > .flash').forEach(e => e.remove())")
    path = os.path.join(OUT, name)
    if clip_selector:
        page.add_style_tag(content=".navbar { position: static !important; }")
        page.locator(clip_selector).first.screenshot(path=path)
    else:
        page.screenshot(path=path, clip={"x": 0, "y": 0, "width": 1280, "height": height or 760})
    print("saved", name)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)

    page.goto(f"{BASE}/login")
    shot(page, "ss_login.png", 640)

    login(page, "rahul@college.edu", "demo123")
    shot(page, "ss_home_rahul.png", 720)

    login(page, "priya@college.edu", "demo123")
    page.evaluate("document.querySelector('.section').scrollIntoView()")
    shot(page, "ss_home_priya.png", 720)

    page.goto(f"{BASE}/search?q=arduno")
    shot(page, "ss_typo_search.png", 700)

    page.goto(f"{BASE}/product/25")
    shot(page, "ss_product.png", 640)

    page.goto(f"{BASE}/sell")
    page.fill("input[name=title]", "Casio fx-991ES calculator - whatsapp me")
    page.fill("textarea[name=description]", "Used for two semesters, works perfectly.")
    page.select_option("select[name=category_id]", "3")
    page.fill("input[name=original_price]", "1200")
    page.fill("input[name=age_months]", "12")
    page.click("text=Suggest price")
    page.wait_for_selector(".suggested")
    page.click("text=Use this price")
    page.wait_for_timeout(1200)
    shot(page, "ss_sell_ai.png", clip_selector="#sellForm")

    login(page, "admin@campuskart.com", "admin123")
    shot(page, "ss_admin_dashboard.png", 760)
    page.goto(f"{BASE}/admin/listings")
    shot(page, "ss_admin_flagged.png", clip_selector=".card")
    page.goto(f"{BASE}/admin/database")
    page.click("text=Searches per user (JOIN + GROUP BY)")
    page.click("text=Run query")
    page.wait_for_load_state("networkidle")
    shot(page, "ss_sql_explorer.png", clip_selector=".card")
    browser.close()
