# LinkedIn Lead Scout

A team dashboard for capturing LinkedIn posts that mention your keywords. It qualifies each post automatically, alerts the team, and tracks follow-up from **New → Reviewed → Contacted → Won/Lost**.

**Stack:** Python FastAPI · SQLite (local) / Postgres (production) · plain-JS dashboard, installable on a phone as a PWA · Docker.

## What it does
- **Accounts and roles:** each member has their own login, as Admin or Member. The first sign-up becomes Admin. Everyone after that needs Admin approval, and you can limit sign-ups to allowed email domains.
- **Sign In with LinkedIn (official OpenID Connect):** members connect their LinkedIn or use it to log in. Only name, photo and email are read. The app **never** asks for a LinkedIn password, stores a cookie, or reads the feed or DMs.
- **How posts get in:**
  0. **Auto-discover (main).** Every hour (configurable) the app searches Google for public LinkedIn posts matching each keyword (`site:linkedin.com/posts "keyword"`, last 24h, 7 days or 30 days). New posts show up in the dashboard by themselves, already tagged, with a team alert. Nobody logs into LinkedIn and LinkedIn itself is not scraped. Each post opens with **LinkedIn's official embed preview**. This needs `SERPER_API_KEY` (free 2,500 searches at serper.dev) or `SERPAPI_API_KEY`.
  1. **Scout session (Playwright, human-driven).** Each member runs `scout/scout_session.py` on their own laptop. A visible Chrome window opens, the member logs in to LinkedIn, IndiaMART or TradeIndia by hand, opens a post, profile or company page, and presses **Enter**. The page is saved locally and sent to Lead Scout as a lead. This follows the Parivestra *Playwright Scouting Session Guide*. Each member gets a personal token from the **Scout session** page. Daily limits are enforced: 60 captures on LinkedIn, 80 on IndiaMART and TradeIndia, 150 on web. The same page generates the group's daily update.
  2. **1-click capture.** Drag the "Save to Lead Scout" button (on the Add lead page) to your bookmarks bar. Then, on any LinkedIn post in your own browser, click it. The real post link, text, author and age arrive pre-filled. One post per click, no automation.
  2. **Paste manually.** Paste the link and text yourself.
  3. **Vendor webhook.** An approved listening tool (e.g. Octolens) sends posts automatically to `POST /api/webhook/ingest`.
- **Auto-qualify:** keyword match, High/Normal intent, lead type (5 types), vertical, campaign model (CPA/CPL/CPI…), GEO, emails/phones/WhatsApp, and a compliance flag (iGaming/crypto/forex/USDT). The **post date is read from the post link itself**.
- **Duplicate block:** the same post in any URL format is never saved twice. You see who added it first and its current status.
- **Tabs:** New (last 7 days, editable) · In progress (with owner) · Old, verify · History (Won/Lost) · All. Plus filters, search and CSV export.
- **Alerts:** in-app bell and pop-up, plus Telegram and Slack (tokens come from env only).
- **Suggested keywords:** similar phrases mined from your captured posts plus common affiliate/performance terms; add one with a single click.
- **Insights:** which keywords and lead types produce wins.
- **Demo sample data:** one click to load or remove; every sample is clearly labelled "Sample data".

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env          # optional locally
uvicorn app.main:app --reload --port 8000
# open http://localhost:8000 → the first sign-up becomes Admin
```
With Docker (app + Postgres): `docker compose up --build`

## Deploy (Render, free tier)
1. Push this folder to GitHub.
2. Render → **New → Blueprint** → choose the repo. `render.yaml` creates the web service and Postgres, and generates `SECRET_KEY` and `WEBHOOK_SECRET`.
3. Set `BASE_URL` to your Render URL (e.g. `https://linkedin-lead-scout.onrender.com`) and redeploy.
4. Open the URL and sign up. That first account becomes Admin.

The app also runs on Railway, Fly.io or any VPS: it is a single Docker container. Set the env vars from `.env.example`, and in production always use Postgres (`DATABASE_URL`) and HTTPS.

## Sign In with LinkedIn setup
1. https://www.linkedin.com/developers/apps → **Create app**. A LinkedIn company page is required.
2. **Products** → add **Sign In with LinkedIn using OpenID Connect**.
3. **Auth** → Authorized redirect URL: `https://YOUR-DOMAIN/auth/linkedin/callback`
4. Copy the Client ID and Secret into `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET`, then restart.

Note: this login does **not** give access to post search or the feed. LinkedIn offers no such API for third-party apps. That is why posts arrive through 1-click capture, manual paste, or an approved vendor.

## Auto-discover setup
1. Sign up at https://serper.dev and copy the API key (2,500 free searches, no card).
2. Set `SERPER_API_KEY` on the server and restart.
3. On the Leads page click **Find posts now**, or wait for the schedule (Settings → Workspace → Auto-discover).

Cost: 1 search per keyword per run. With 5 keywords every hour that's about 3,600 searches a month, roughly $3.60 on Serper's paid credits.

Coverage is whatever Google has indexed. Some brand-new or non-public posts won't show up, and 1-click capture covers those.

Note: Google's own Custom Search JSON API is closed to new customers and shuts down on 1 Jan 2027, which is why this uses Serper or SerpAPI.

## Telegram alerts
Create a bot with @BotFather and add it to your team group. Get the chat id (for example via `https://api.telegram.org/bot<TOKEN>/getUpdates`). Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, then use Settings → Alerts → **Send test alert**.

## Vendor webhook
```bash
curl -X POST https://YOUR-DOMAIN/api/webhook/ingest \
  -H "Content-Type: application/json" -H "X-Webhook-Secret: $WEBHOOK_SECRET" \
  -d '{"items":[{"url":"https://www.linkedin.com/feed/update/urn:li:activity:7300000000000000000/","text":"Looking for performance marketing agency","author":{"name":"Jane"},"posted_at":"2026-11-25T08:00:00Z"}]}'
```
The endpoint accepts `url|post_url|link`, `text|content|body`, `author|author.name`, and `posted_at|timestamp`. Posts without a tracked keyword are ignored. A vendor-specific format may need a small mapping. Before buying, get the vendor's data source and compliance in writing.

## Tests
```bash
pip install -r requirements-dev.txt && playwright install chromium
pytest tests/test_parsing.py
# E2E (localhost only, fresh DB): start the server, then
pytest tests/test_e2e.py     # sign up → add lead → shows in list → duplicate rejected
```

## API docs
Interactive docs are at `/api/docs`.

## Compliance notes
- The app does not scrape or automate LinkedIn, and it collects no LinkedIn passwords, cookies or OTPs. Doing any of that risks account restriction under LinkedIn's terms.
- Contacts are for business follow-up only: no bulk WhatsApp, auto-email or auto-DM.
- Posts flagged "Compliance review" need company approval before anyone makes contact.
- Do a privacy/legal check before real use, and remove sample data.
