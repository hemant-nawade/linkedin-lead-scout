"""SmartScout / Lead Scout — human-driven Playwright scouting session.

Based on the Parivestra "Playwright Scouting Session Guide" (Group 6). You drive the browser:
log in by hand, search by hand, open a page, then press Enter here to save it.
Every capture is saved locally (captures/<date>/) AND sent to Lead Scout, where it becomes a
lead with keywords, intent, lead type and contacts detected automatically.

Run:
    python scout_session.py --site linkedin --by "riya" --tag "affiliate-partners"

Lead Scout connection (one time): Lead Scout → Settings → Profile → "Scout session token".
    Windows:  setx LEADSCOUT_URL "https://linkedin-lead-scout.onrender.com"
              setx LEADSCOUT_TOKEN "lsk_..."      (then open a NEW terminal)
    Mac/Linux: export LEADSCOUT_URL=... ; export LEADSCOUT_TOKEN=...
Without these, captures are only saved locally.

The script never auto-scrolls, auto-clicks, auto-searches, runs headless, or handles logins/OTPs.
"""
import argparse
import datetime
import json
import os
import pathlib

from playwright.sync_api import sync_playwright

# ---- settings -------------------------------------------------
SITES = {
    "linkedin":   {"start": "https://www.linkedin.com/feed/", "cap": 60},
    "indiamart":  {"start": "https://www.indiamart.com/",     "cap": 80},
    "tradeindia": {"start": "https://www.tradeindia.com/",    "cap": 80},
    "web":        {"start": "about:blank",                    "cap": 150},
}
BASE = pathlib.Path.home() / ".smartscout"      # private login profiles, outside the project
OUTDIR = pathlib.Path("captures")
SERVER = os.getenv("LEADSCOUT_URL", "").rstrip("/")
TOKEN = os.getenv("LEADSCOUT_TOKEN", "")


def page_type(site, url):
    rules = {"linkedin": [("/posts/", "post"), ("/feed/update/", "post"), ("/in/", "person"),
                          ("/company/", "company"), ("/search/", "search"), ("/jobs/", "job")],
             "indiamart": [("/proddetail/", "product"), ("/search", "search")],
             "tradeindia": [("/products/", "product"), ("/search", "search")]}
    for key, name in rules.get(site, []):
        if key in url:
            return name
    return "page"


def read_text(page):
    # main content first, whole body as fallback
    for sel in ("main", "[role=main]", "body"):
        try:
            t = page.inner_text(sel, timeout=2500)
            if len(t.strip()) > 80:
                return t
        except Exception:
            pass
    return ""


def today_count(site):
    d = OUTDIR / datetime.date.today().isoformat()
    return len(list(d.glob(f"{site}_*.json"))) if d.exists() else 0


def upload(rec):
    """Send one capture to Lead Scout. Returns a short message for the terminal."""
    if not (SERVER and TOKEN):
        return "local only (set LEADSCOUT_URL and LEADSCOUT_TOKEN to send to Lead Scout)"
    import requests
    try:
        r = requests.post(f"{SERVER}/api/captures", json=rec, timeout=60,
                          headers={"Authorization": f"Bearer {TOKEN}"})
        d = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    except Exception as e:  # noqa: BLE001
        return f"upload failed, kept locally: {e}"
    if r.status_code == 401:
        return "token rejected: generate a new one in Lead Scout → Settings → Profile"
    if d.get("status") == "created":
        kw = ", ".join(d.get("keywords") or []) or "no keyword"
        hi = " · HIGH intent" if d.get("intent") == "High" else ""
        return f"→ Lead Scout #{d['lead_id']} [{kw}{hi}] ({d['count_today']}/{d['cap']} today on server)"
    if d.get("status") == "duplicate":
        return f"→ already in Lead Scout: {d.get('detail')}"
    if d.get("status") == "limit":
        return f"→ {d.get('detail')}"
    return f"upload error {r.status_code}: {d.get('detail') or r.text[:120]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", choices=SITES, required=True)
    ap.add_argument("--by", default="intern", help="your name, saved with each capture")
    ap.add_argument("--tag", default="", help="campaign tag, e.g. pune-schools")
    a = ap.parse_args()
    cfg = SITES[a.site]
    profile = BASE / "profiles" / a.site
    profile.mkdir(parents=True, exist_ok=True)
    day = OUTDIR / datetime.date.today().isoformat()
    day.mkdir(parents=True, exist_ok=True)

    print("Lead Scout:", SERVER if (SERVER and TOKEN) else "not connected (captures stay local)")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(profile), headless=False,            # always visible
            viewport={"width": 1366, "height": 860})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(cfg["start"])
        print("Log in by hand if asked. Then open any page you want to save.")
        print("[Enter] capture   [s] capture + screenshot   [q] quit")

        while True:
            cmd = input("> ").strip().lower()
            if cmd == "q":
                break
            n = today_count(a.site)
            if n >= cfg["cap"]:
                print(f"Daily limit {cfg['cap']} reached. Stop for today.")
                continue
            page = ctx.pages[-1]                     # the tab you are looking at
            text = read_text(page)
            if not text:
                print("Nothing readable yet. Wait for the page to load.")
                continue
            rec = {"site": a.site, "url": page.url,
                   "page_type": page_type(a.site, page.url),
                   "title": page.title(), "text": text[:20000],
                   "tag": a.tag, "captured_by": a.by,
                   "captured_at": datetime.datetime.now().isoformat(timespec="seconds")}
            stem = day / f"{a.site}_{n + 1:04d}"
            stem.with_suffix(".json").write_text(
                json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
            if cmd == "s":
                page.screenshot(path=str(stem.with_suffix(".png")))
            print(f"Saved {stem.name} ({n + 1}/{cfg['cap']} today) [{rec['page_type']}]  {upload(rec)}")
        ctx.close()


if __name__ == "__main__":
    main()
