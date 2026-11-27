# Scout session (human-driven Playwright)

Runs on **your own laptop**, not on the server. You drive a normal, visible Chrome window, and the script saves a page only when you press Enter. Each saved page lands in Lead Scout as a lead.

## Setup (one time, ~15 min)

```bash
# Windows (PowerShell)
mkdir smartscout-session; cd smartscout-session
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
```

Download `scout_session.py` from Lead Scout (Scout session page) or copy it from this folder.

In Lead Scout, go to **Settings → Profile → Scout session token → Generate**, then:

```powershell
setx LEADSCOUT_URL "https://linkedin-lead-scout.onrender.com"
setx LEADSCOUT_TOKEN "lsk_..."
```

Open a **new** terminal after running `setx` so it picks up the values.

## Run

```bash
python scout_session.py --site linkedin --by "riya" --tag "affiliate-partners"
```

- `Enter`: save the page and send it to Lead Scout
- `s`: same as Enter, plus a screenshot
- `q`: quit

## Rules (from the Parivestra guide)

- Use your own real LinkedIn account and log in by hand. Type the OTP yourself.
- Never type a password into the terminal.
- Limits per day: 60 LinkedIn captures and 25 searches.
- If LinkedIn shows a warning or a CAPTCHA, stop for the day and tell your lead.
- Never share the `~/.smartscout` profile folder or your token.
