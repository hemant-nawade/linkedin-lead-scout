"""Auto-discovery of PUBLIC LinkedIn posts — no LinkedIn login, no LinkedIn scraping.

How it works: for every tracked keyword we ask a Google search API (Serper.dev or SerpAPI)
for  site:linkedin.com/posts "<keyword>"  restricted to the last day/week/month.
Google has already indexed these public posts; we only read the search result
(link, title, snippet). The full post is shown in the dashboard with LinkedIn's own
official embed (iframe), loaded in the viewer's browser.
"""
import asyncio
import logging
import os
import re
from collections import Counter
from datetime import timedelta
from typing import Optional

import httpx
from sqlalchemy.exc import IntegrityError

from . import parsing
from .db import SessionLocal, utcnow

log = logging.getLogger("leadscout.discovery")

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "").strip()


def provider_name() -> Optional[str]:
    if SERPER_API_KEY:
        return "serper"
    if SERPAPI_API_KEY:
        return "serpapi"
    return None


def build_query(keyword: str) -> str:
    return f'site:linkedin.com/posts "{keyword}"'


def search(keyword: str, window: str = "w", country: str = "in", num: int = 20) -> list[dict]:
    """Returns [{url,title,snippet,date_text}] from the configured provider."""
    q = build_query(keyword)
    p = provider_name()
    if p == "serper":
        r = httpx.post("https://google.serper.dev/search", timeout=25,
                       headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                       json={"q": q, "num": num, "gl": country, "tbs": f"qdr:{window}"})
        r.raise_for_status()
        items = r.json().get("organic", [])
        return [{"url": i.get("link", ""), "title": i.get("title", ""), "snippet": i.get("snippet", ""),
                 "date_text": i.get("date", "")} for i in items]
    if p == "serpapi":
        r = httpx.get("https://serpapi.com/search.json", timeout=25, params={
            "engine": "google", "q": q, "num": num, "gl": country, "tbs": f"qdr:{window}",
            "api_key": SERPAPI_API_KEY})
        r.raise_for_status()
        items = r.json().get("organic_results", [])
        return [{"url": i.get("link", ""), "title": i.get("title", ""), "snippet": i.get("snippet", ""),
                 "date_text": i.get("date", "")} for i in items]
    raise RuntimeError("No search API key set (SERPER_API_KEY or SERPAPI_API_KEY)")


NOT_NAME = {"campaign", "campaigns", "available", "partners", "partner", "opportunity", "opportunities", "hiring",
            "looking", "live", "required", "wanted", "needed", "projects", "project", "offers", "vendors", "traffic"}
_TITLE_TAIL = re.compile(r"\s*[|\-–]\s*(LinkedIn|\d+\s+(comments?|reactions?|likes?))\s*$", re.I)


def split_title(title: str, url: str) -> tuple[str, str]:
    """LinkedIn post titles in Google look like
       'Shubham Kumar on LinkedIn: Looking for Quality Traffic Partners …'  or
       'Looking for Quality Traffic Partners … | Shubham Kumar | 12 comments'.
    Returns (author, headline_text)."""
    t = (title or "").strip()
    for _ in range(3):
        t = _TITLE_TAIL.sub("", t)
    m = re.match(r"^(.{2,80}?)\s+on\s+LinkedIn\s*:\s*(.*)$", t, re.I)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    name_re = re.compile(r"^[A-Z][\w.'’-]*(?:\s+[A-Z][\w.'’-]*){0,3}$")
    m = re.match(r"^(.*?)\s+[-–]\s+([A-Z][\w.'’-]+(?:\s+[A-Z][\w.'’-]+){0,3})$", t)
    if m and name_re.match(m.group(2)):
        return m.group(2), m.group(1)
    parts = [x.strip() for x in t.split(" | ") if x.strip()]
    for cand in reversed(parts[1:]):
        if name_re.match(cand) and not re.search(r"\d", cand) and not (set(cand.lower().split()) & NOT_NAME):
            return cand, " | ".join(x for x in parts if x != cand)
    # fall back to the URL slug: /posts/shubham-kumar-123_looking-for-...
    slug = re.search(r"linkedin\.com/posts/([a-z0-9-]+?)(?:-[a-z0-9]{6,})?_", url or "", re.I)
    author = slug.group(1).replace("-", " ").title() if slug else ""
    return author, t


def run_discovery(get_config, create_lead, create_notification, deliver_external, save_status) -> dict:
    """One full pass over all keywords. Safe to call from a thread."""
    db = SessionLocal()
    stats = {"started_at": utcnow().isoformat() + "Z", "provider": provider_name(), "queries": 0,
             "results": 0, "created": 0, "duplicates": 0, "skipped_old": 0, "skipped_other": 0, "errors": []}
    try:
        cfg = get_config(db)
        if not provider_name():
            stats["errors"].append("No search API key configured")
            return stats
        max_age = timedelta(days=int(cfg.get("discovery_max_age_days", 30)))
        window = cfg.get("discovery_window", "w")
        country = cfg.get("discovery_country", "in")
        for kw in cfg["keywords"]:
            try:
                items = search(kw, window, country)
            except Exception as e:  # noqa: BLE001 — keep going with other keywords
                stats["errors"].append(f"{kw}: {e}"[:200])
                continue
            stats["queries"] += 1
            stats["results"] += len(items)
            for it in items:
                url = it["url"]
                if not parsing.is_linkedin_url(url) or not parsing.linkedin_post_id(url):
                    stats["skipped_other"] += 1
                    continue
                pid = parsing.linkedin_post_id(url)[1]
                posted = parsing.date_from_post_id(pid)
                if posted and utcnow() - posted > max_age:
                    stats["skipped_old"] += 1
                    continue
                author, headline_text = split_title(it["title"], url)
                text = headline_text
                snip = (it.get("snippet") or "").strip()
                if snip and snip[:40].lower() not in text.lower():
                    text = f"{text}\n\n{snip}" if text else snip
                try:
                    lead, dup = create_lead(db, {"post_url": url, "post_text": text, "author_name": author,
                                                 "post_age_text": "" if posted else it.get("date_text", ""),
                                                 "force_keywords": [kw]}, None, "search", cfg)
                except IntegrityError:
                    db.rollback()
                    stats["duplicates"] += 1
                    continue
                if dup:
                    stats["duplicates"] += 1
                    continue
                stats["created"] += 1
                n = create_notification(db, lead)
                deliver_external(n.id)
        return stats
    finally:
        stats["finished_at"] = utcnow().isoformat() + "Z"
        try:
            save_status(db, stats)
        finally:
            db.close()


async def scheduler_loop(get_config, runner) -> None:
    """Runs discovery every N minutes (from settings). Single-process app → single scheduler."""
    await asyncio.sleep(20)
    while True:
        minutes = 60
        try:
            db = SessionLocal()
            try:
                cfg = get_config(db)
            finally:
                db.close()
            minutes = max(15, int(cfg.get("discovery_interval_min", 60)))
            if cfg.get("discovery_enabled", True) and provider_name():
                await asyncio.get_running_loop().run_in_executor(None, runner)
        except Exception as e:  # noqa: BLE001
            log.warning("Discovery loop error: %s", e)
        await asyncio.sleep(minutes * 60)


# ------------------------------------------------------------------ keyword suggestions
# Phrases seen in the kind of posts HR shared (traffic partners, direct advertisers, vendor onboarding…)
CURATED_SUGGESTIONS = [
    "traffic partners", "CPA network", "affiliate network", "direct advertisers", "media buyers",
    "publishers", "affiliate partners", "campaign execution partners", "execution vendors",
    "vendor onboarding", "demat campaign", "CPI campaign", "CPA campaign", "campaign live",
    "performance marketing campaigns", "performance marketing agency", "Meta ads agency",
    "influencer marketing agency", "lead generation campaign", "iGaming affiliate",
    "direct campaigns", "brand partnerships", "sub-publishers", "app install campaign",
]

STOP = set("""a an the and or for to of in on with by at from is are we our you your us i me my this that these those
be have has will can as it its if not no all any more most into via per who what how let let's lets connect dm
looking seeking available new now also across various multiple long term please feel free get just like
cpa cpi cps cpe cpl cpc cpm models model agencies whatsapp email contact details
""".split())


def suggest_keywords(texts: list[str], existing: list[str], limit: int = 20) -> list[dict]:
    """Frequent 2–3 word phrases from captured posts + curated list, minus existing keywords."""
    have = {k.lower() for k in existing}
    counts: Counter = Counter()
    for t in texts:
        words = [w for w in re.findall(r"[a-z][a-z0-9+-]{1,}", (t or "").lower())]
        seen = set()
        for n in (2, 3):
            for i in range(len(words) - n + 1):
                g = words[i:i + n]
                if g[0] in STOP or g[-1] in STOP or any(len(w) < 3 for w in g):
                    continue
                ph = " ".join(g)
                if ph not in seen:
                    seen.add(ph)
                    counts[ph] += 1
    mined = [(p, c) for p, c in counts.most_common(80)
             if c >= 3 and p not in have and not any(p in h or h in p for h in have)]
    out, used = [], set()
    for p, c in mined[: limit // 2]:
        out.append({"keyword": p, "source": "from your leads", "count": c})
        used.add(p)
    for p in CURATED_SUGGESTIONS:
        if len(out) >= limit:
            break
        if p.lower() not in have and p.lower() not in used:
            out.append({"keyword": p, "source": "suggested", "count": None})
    return out
