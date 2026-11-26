"""New-lead alerts: in-app (always) + Telegram + Slack (when configured via env)."""
import html
import logging

import httpx

from .config import settings
from .db import SessionLocal
from .models import Lead, Notification

log = logging.getLogger("leadscout.notify")


def _lead_lines(lead: Lead) -> tuple[str, str]:
    title = f"New {'HIGH-intent ' if lead.intent == 'High' else ''}lead: {lead.author_name or 'Unknown author'}"
    kw = ", ".join(lead.keywords or []) or "—"
    types = ", ".join(lead.lead_types or []) or "—"
    snippet = (lead.post_text or "").strip().replace("\n", " ")
    if len(snippet) > 220:
        snippet = snippet[:220] + "…"
    body = f"Keyword: {kw} | Type: {types}\n{snippet}"
    return title, body


def create_notification(db, lead: Lead) -> Notification:
    title, body = _lead_lines(lead)
    n = Notification(lead_id=lead.id, title=title, body=body, channels={
        "in_app": "sent",
        "telegram": "pending" if settings.telegram_enabled else "off",
        "slack": "pending" if settings.slack_enabled else "off",
    })
    db.add(n)
    db.commit()
    return n


def deliver_external(notification_id: int) -> None:
    """Runs as a background task after the response is sent."""
    db = SessionLocal()
    try:
        n = db.get(Notification, notification_id)
        if not n:
            return
        lead = db.get(Lead, n.lead_id) if n.lead_id else None
        link = f"{settings.BASE_URL}/#/lead/{lead.id}" if lead else settings.BASE_URL
        post = lead.post_url if lead else ""
        ch = dict(n.channels or {})
        if settings.telegram_enabled:
            text = (f"<b>{html.escape(n.title)}</b>\n{html.escape(n.body)}\n\n"
                    f"<a href=\"{html.escape(post)}\">Open post</a> · <a href=\"{html.escape(link)}\">Open in Lead Scout</a>")
            try:
                r = httpx.post(f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                               json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text,
                                     "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=10)
                ch["telegram"] = "sent" if r.status_code == 200 else f"failed ({r.status_code})"
            except httpx.HTTPError as e:
                ch["telegram"] = "failed"
                log.warning("Telegram failed: %s", e)
        if settings.slack_enabled:
            try:
                r = httpx.post(settings.SLACK_WEBHOOK_URL, json={
                    "text": f"*{n.title}*\n{n.body}\n<{post}|Open post> · <{link}|Open in Lead Scout>"}, timeout=10)
                ch["slack"] = "sent" if r.status_code < 300 else f"failed ({r.status_code})"
            except httpx.HTTPError as e:
                ch["slack"] = "failed"
                log.warning("Slack failed: %s", e)
        n.channels = ch
        db.commit()
    finally:
        db.close()


def send_test(channel: str) -> str:
    if channel == "telegram":
        if not settings.telegram_enabled:
            return "Telegram not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)"
        r = httpx.post(f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                       json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": "✅ Lead Scout test alert"}, timeout=10)
        return "sent" if r.status_code == 200 else f"failed ({r.status_code}): {r.text[:160]}"
    if channel == "slack":
        if not settings.slack_enabled:
            return "Slack not configured (set SLACK_WEBHOOK_URL)"
        r = httpx.post(settings.SLACK_WEBHOOK_URL, json={"text": "✅ Lead Scout test alert"}, timeout=10)
        return "sent" if r.status_code < 300 else f"failed ({r.status_code})"
    return "unknown channel"
