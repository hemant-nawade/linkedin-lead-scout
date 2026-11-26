"""LinkedIn Lead Scout — FastAPI app (API + dashboard)."""
import asyncio
import csv
import threading
import io
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import discovery, parsing
from .auth import (admin_user, any_user, clear_session, current_user, hash_password, optional_user,
                   set_session, verify_password)
from .config import settings
from .db import Base, SessionLocal, engine, get_db, utcnow
from .models import Activity, AppSetting, Lead, Notification, NotificationRead, User
from .notify import create_notification, deliver_external, send_test

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("leadscout")

STATIC = Path(__file__).resolve().parent.parent / "static"
STATUSES = ["New", "Reviewed", "Contacted", "Won", "Lost"]
LEAD_TYPES = list(parsing.LEAD_TYPE_RULES.keys())

app = FastAPI(title=settings.APP_NAME, docs_url="/api/docs", redoc_url=None)


# ======================================================================= startup
@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if settings.ADMIN_EMAIL and settings.ADMIN_PASSWORD and not db.scalar(select(func.count(User.id))):
            db.add(User(email=settings.ADMIN_EMAIL, name=settings.ADMIN_NAME, role="admin", approved=True,
                        password_hash=hash_password(settings.ADMIN_PASSWORD)))
            db.commit()
            log.info("Bootstrap admin created: %s", settings.ADMIN_EMAIL)
    finally:
        db.close()
    asyncio.get_event_loop().create_task(discovery.scheduler_loop(get_config, _run_discovery))


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["X-Frame-Options"] = "DENY"
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


# ======================================================================= app settings
DEFAULT_CONFIG = {
    "keywords": parsing.DEFAULT_KEYWORDS,
    "intent_words": parsing.DEFAULT_INTENT_WORDS,
    "active_days": 7,
    "allowed_domains": [],          # e.g. ["parivestra.com"]; empty = anyone may sign up (still needs approval)
    "auto_approve_domains": False,  # auto-approve signups from allowed domains
    "rtds_meaning": "",             # confirm with requirement owner
    # Auto-discovery of public LinkedIn posts via a Google search API
    "discovery_enabled": True,
    "discovery_interval_min": 60,
    "discovery_window": "w",        # d = last 24h, w = last week, m = last month
    "discovery_country": "in",
    "discovery_max_age_days": 30,
}


def get_config(db: Session) -> dict:
    row = db.get(AppSetting, "config")
    cfg = dict(DEFAULT_CONFIG)
    if row:
        cfg.update(row.value or {})
    return cfg


def save_config(db: Session, cfg: dict) -> None:
    row = db.get(AppSetting, "config")
    if row:
        row.value = cfg
    else:
        db.add(AppSetting(key="config", value=cfg))
    db.commit()


# ======================================================================= serializers
def user_public(u: Optional[User]) -> Optional[dict]:
    if not u:
        return None
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role,
            "picture": u.linkedin_picture}


def user_full(u: User) -> dict:
    d = user_public(u)
    d.update({
        "approved": u.approved, "active": u.active,
        "linkedin": {"connected": bool(u.linkedin_sub), "name": u.linkedin_name,
                     "email": u.linkedin_email, "picture": u.linkedin_picture,
                     "connected_at": iso(u.linkedin_connected_at)},
        "created_at": iso(u.created_at), "last_login_at": iso(u.last_login_at),
        "has_password": bool(u.password_hash),
    })
    return d


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


def lead_tab(lead: Lead, active_days: int) -> str:
    if lead.status in ("Won", "Lost"):
        return "history"
    if lead.status in ("Reviewed", "Contacted"):
        return "progress"
    if lead.post_date and lead.post_date < utcnow() - timedelta(days=active_days):
        return "old"
    return "new"


def lead_dict(lead: Lead, active_days: int, full: bool = False) -> dict:
    d = {
        "id": lead.id, "post_url": lead.post_url, "author_name": lead.author_name,
        "author_headline": lead.author_headline, "author_url": lead.author_url,
        "post_text": lead.post_text if full else (lead.post_text or "")[:600],
        "text_truncated": (not full) and len(lead.post_text or "") > 600,
        "keywords": lead.keywords or [], "intent": lead.intent, "intent_words": lead.intent_words or [],
        "lead_types": lead.lead_types or [], "vertical": lead.vertical,
        "campaign_models": lead.campaign_models or [], "geo": lead.geo,
        "post_age_text": lead.post_age_text, "post_date": iso(lead.post_date),
        "age_label": parsing.human_age(lead.post_date),
        "contacts": lead.contacts or {}, "compliance_flag": lead.compliance_flag,
        "compliance_terms": lead.compliance_terms or [], "source": lead.source,
        "is_sample": lead.is_sample, "status": lead.status, "notes": lead.notes,
        "added_by": user_public(lead.added_by), "owner": user_public(lead.owner),
        "captured_at": iso(lead.captured_at), "updated_at": iso(lead.updated_at),
        "tab": lead_tab(lead, active_days),
    }
    d["old_verify"] = d["tab"] == "old"
    pid = parsing.linkedin_post_id(lead.post_url)
    d["embed_url"] = f"https://www.linkedin.com/embed/feed/update/urn:li:{pid[0]}:{pid[1]}" if pid else None
    return d


def log_activity(db: Session, lead_id: int, user: Optional[User], action: str) -> None:
    db.add(Activity(lead_id=lead_id, user_id=user.id if user else None, action=action))


# ======================================================================= rate limit (login)
_attempts: dict[str, list[float]] = defaultdict(list)


def rate_limit(key: str, limit: int = 8, window: int = 300) -> None:
    now = time.time()
    _attempts[key] = [t for t in _attempts[key] if now - t < window]
    if len(_attempts[key]) >= limit:
        raise HTTPException(429, "Too many attempts. Try again in a few minutes.")
    _attempts[key].append(now)


# ======================================================================= public config
@app.get("/api/config/public")
def public_config(db: Session = Depends(get_db)):
    return {"app_name": settings.APP_NAME, "linkedin_enabled": settings.linkedin_enabled,
            "first_run": not db.scalar(select(func.count(User.id)))}


@app.get("/healthz")
def healthz():
    return {"ok": True}


# ======================================================================= auth
class SignupIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _domain_allowed(email: str, cfg: dict) -> bool:
    doms = [d.lower().lstrip("@") for d in cfg.get("allowed_domains") or [] if d.strip()]
    return not doms or email.split("@")[-1].lower() in doms


def _admin_alert(db: Session, title: str, body: str) -> None:
    db.add(Notification(title=title, body=body, channels={"in_app": "sent"}))
    db.commit()


@app.post("/api/auth/signup")
def signup(data: SignupIn, request: Request, db: Session = Depends(get_db)):
    rate_limit("signup:" + (request.client.host if request.client else "?"), 10, 600)
    email = data.email.lower()
    cfg = get_config(db)
    first = not db.scalar(select(func.count(User.id)))
    if not first and not _domain_allowed(email, cfg):
        raise HTTPException(403, "Only company email addresses can sign up. Ask your admin.")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    approved = first or (cfg.get("auto_approve_domains") and bool(cfg.get("allowed_domains")))
    user = User(email=email, name=data.name.strip(), password_hash=hash_password(data.password),
                role="admin" if first else "member", approved=bool(approved), last_login_at=utcnow())
    db.add(user)
    db.commit()
    if not user.approved:
        _admin_alert(db, f"New member waiting for approval: {user.name}", f"{user.email} signed up. Approve in Team.")
    resp = JSONResponse({"user": user_full(user)})
    set_session(resp, user)
    return resp


@app.post("/api/auth/login")
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    rate_limit("login:" + data.email.lower())
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    if not user.active:
        raise HTTPException(403, "This account is deactivated")
    user.last_login_at = utcnow()
    db.commit()
    resp = JSONResponse({"user": user_full(user)})
    set_session(resp, user)
    return resp


@app.post("/api/auth/logout")
def logout():
    resp = JSONResponse({"ok": True})
    clear_session(resp)
    return resp


@app.get("/api/me")
def me(user: User = Depends(any_user)):
    return {"user": user_full(user)}


class PasswordIn(BaseModel):
    current_password: str = ""
    new_password: str = Field(min_length=8, max_length=128)


@app.post("/api/me/password")
def change_password(data: PasswordIn, user: User = Depends(any_user), db: Session = Depends(get_db)):
    if user.password_hash and not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is wrong")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    resp = JSONResponse({"ok": True})
    set_session(resp, user)
    return resp


@app.delete("/api/me/linkedin")
def disconnect_linkedin(user: User = Depends(any_user), db: Session = Depends(get_db)):
    if not user.password_hash:
        raise HTTPException(400, "Set a password first, otherwise you can't log in after disconnecting")
    user.linkedin_sub = user.linkedin_name = user.linkedin_email = user.linkedin_picture = None
    user.linkedin_connected_at = None
    db.commit()
    return {"user": user_full(user)}


# ----------------------------------------------------------------------- Sign In with LinkedIn (OIDC)
@app.get("/auth/linkedin/start")
def linkedin_start(mode: str = "login", user: Optional[User] = Depends(optional_user)):
    if not settings.linkedin_enabled:
        return RedirectResponse("/#/login?error=" + "LinkedIn sign-in is not configured yet")
    if mode == "connect" and not user:
        return RedirectResponse("/#/login")
    state = secrets.token_urlsafe(24)
    params = {"response_type": "code", "client_id": settings.LINKEDIN_CLIENT_ID,
              "redirect_uri": settings.LINKEDIN_REDIRECT_URI, "state": state,
              "scope": "openid profile email"}
    resp = RedirectResponse("https://www.linkedin.com/oauth/v2/authorization?" + urlencode(params))
    resp.set_cookie("ls_oauth", f"{state}:{'connect' if mode == 'connect' else 'login'}", max_age=600,
                    httponly=True, samesite="lax", secure=settings.COOKIE_SECURE, path="/")
    return resp


@app.get("/auth/linkedin/callback")
def linkedin_callback(request: Request, code: str = "", state: str = "", error: str = "",
                      error_description: str = "", db: Session = Depends(get_db),
                      user: Optional[User] = Depends(optional_user)):
    def fail(msg: str, to: str = "/#/login"):
        sep = "&" if "?" in to else "?"
        r = RedirectResponse(f"{to}{sep}error={msg}")
        r.delete_cookie("ls_oauth", path="/")
        return r

    cookie = request.cookies.get("ls_oauth", "")
    saved_state, _, mode = cookie.partition(":")
    back = "/#/settings/profile" if mode == "connect" else "/#/login"
    if error:
        return fail(error_description or error, back)
    if not code or not state or not saved_state or not secrets.compare_digest(state, saved_state):
        return fail("LinkedIn sign-in expired, please try again", back)
    try:
        tok = httpx.post("https://www.linkedin.com/oauth/v2/accessToken", data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
            "client_id": settings.LINKEDIN_CLIENT_ID, "client_secret": settings.LINKEDIN_CLIENT_SECRET,
        }, timeout=15)
        tok.raise_for_status()
        access = tok.json()["access_token"]
        info = httpx.get("https://api.linkedin.com/v2/userinfo",
                         headers={"Authorization": f"Bearer {access}"}, timeout=15)
        info.raise_for_status()
        p = info.json()
    except (httpx.HTTPError, KeyError, ValueError) as e:
        log.warning("LinkedIn OIDC failed: %s", e)
        return fail("Could not verify your LinkedIn account", back)
    # We keep only basic profile. The access token is NOT stored.
    sub, li_email = p.get("sub"), (p.get("email") or "").lower()
    li_name = p.get("name") or " ".join(x for x in [p.get("given_name"), p.get("family_name")] if x)
    owner = db.scalar(select(User).where(User.linkedin_sub == sub))

    def link(u: User):
        u.linkedin_sub, u.linkedin_name, u.linkedin_email = sub, li_name, li_email or None
        u.linkedin_picture, u.linkedin_connected_at = p.get("picture"), utcnow()

    if mode == "connect":
        if not user:
            return fail("Please log in first")
        if owner and owner.id != user.id:
            return fail("This LinkedIn account is already linked to another member", back)
        link(user)
        db.commit()
        r = RedirectResponse("/#/settings/profile?connected=1")
        r.delete_cookie("ls_oauth", path="/")
        return r

    # login mode
    target = owner
    if not target and li_email and p.get("email_verified", False):
        target = db.scalar(select(User).where(User.email == li_email))
        if target:
            link(target)
    if not target:
        cfg = get_config(db)
        first = not db.scalar(select(func.count(User.id)))
        if not first and li_email and not _domain_allowed(li_email, cfg):
            # Personal LinkedIn email: still create, but pending admin approval
            pass
        target = User(email=li_email or f"{sub}@linkedin.local", name=li_name or "LinkedIn user",
                      role="admin" if first else "member", approved=first)
        link(target)
        db.add(target)
        db.commit()
        if not target.approved:
            _admin_alert(db, f"New member waiting for approval: {target.name}",
                         f"Signed in with LinkedIn ({li_email or 'no email'}). Approve in Team.")
    if not target.active:
        return fail("This account is deactivated")
    target.last_login_at = utcnow()
    db.commit()
    r = RedirectResponse("/#/")
    r.delete_cookie("ls_oauth", path="/")
    set_session(r, target)
    return r


# ======================================================================= settings & integrations
class ConfigIn(BaseModel):
    keywords: list[str]
    intent_words: list[str]
    active_days: int = Field(ge=1, le=365)
    allowed_domains: list[str] = []
    auto_approve_domains: bool = False
    rtds_meaning: str = ""
    discovery_enabled: bool = True
    discovery_interval_min: int = Field(default=60, ge=15, le=1440)
    discovery_window: str = Field(default="w", pattern="^[dwm]$")
    discovery_country: str = Field(default="in", max_length=5)
    discovery_max_age_days: int = Field(default=30, ge=1, le=365)

    @field_validator("keywords", "intent_words", "allowed_domains")
    @classmethod
    def clean(cls, v):
        out = []
        for s in v:
            s = s.strip()
            if s and s.lower() not in [o.lower() for o in out]:
                out.append(s[:80])
        return out


@app.get("/api/settings")
def read_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"config": get_config(db), "statuses": STATUSES, "lead_types": LEAD_TYPES,
            "verticals": list(parsing.VERTICAL_RULES.keys()),
            "campaign_models": ["CPA", "CPL", "CPI", "CPS", "CPE", "CPC", "CPM", "RevShare"]}


@app.put("/api/settings")
def update_settings(data: ConfigIn, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    if not data.keywords:
        raise HTTPException(400, "Add at least one keyword")
    cfg = get_config(db)
    cfg.update(data.model_dump())
    save_config(db, cfg)
    return {"config": cfg}


@app.get("/api/integrations")
def integrations(user: User = Depends(current_user)):
    return {
        "linkedin": {"enabled": settings.linkedin_enabled, "redirect_uri": settings.LINKEDIN_REDIRECT_URI},
        "telegram": {"enabled": settings.telegram_enabled},
        "slack": {"enabled": settings.slack_enabled},
        "webhook": {"enabled": bool(settings.WEBHOOK_SECRET),
                    "url": f"{settings.BASE_URL}/api/webhook/ingest"},
        "base_url": settings.BASE_URL,
        "search": {"enabled": bool(discovery.provider_name()), "provider": discovery.provider_name()},
    }


class TestIn(BaseModel):
    channel: str


@app.post("/api/integrations/test")
def integrations_test(data: TestIn, user: User = Depends(admin_user)):
    try:
        return {"result": send_test(data.channel)}
    except httpx.HTTPError as e:
        return {"result": f"failed: {e}"}


# ======================================================================= leads
class AnalyzeIn(BaseModel):
    text: str = ""
    url: str = ""
    age_text: str = ""


def _dup_info(db: Session, norm_url: str) -> Optional[dict]:
    if not norm_url:
        return None
    lead = db.scalar(select(Lead).where(Lead.post_url == norm_url))
    if not lead:
        return None
    return {"lead_id": lead.id, "status": lead.status, "added_by": lead.added_by.name if lead.added_by else lead.source,
            "owner": lead.owner.name if lead.owner else None, "captured_at": iso(lead.captured_at),
            "message": f"Already saved by {lead.added_by.name if lead.added_by else lead.source} · status {lead.status}"}


@app.post("/api/leads/analyze")
def analyze(data: AnalyzeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cfg = get_config(db)
    a = parsing.analyze(data.text, data.url, data.age_text, cfg["keywords"], cfg["intent_words"])
    a["duplicate"] = _dup_info(db, a["normalized_url"])
    a["is_linkedin"] = parsing.is_linkedin_url(data.url) if data.url else None
    return a


class LeadIn(BaseModel):
    post_url: str = Field(min_length=8, max_length=600)
    post_text: str = Field(min_length=5, max_length=20000)
    author_name: str = Field(default="", max_length=200)
    author_headline: str = Field(default="", max_length=300)
    author_url: str = Field(default="", max_length=600)
    post_age_text: str = Field(default="", max_length=20)
    post_date: Optional[datetime] = None
    lead_types: Optional[list[str]] = None
    vertical: Optional[str] = None
    campaign_models: Optional[list[str]] = None
    geo: Optional[str] = None
    notes: str = ""
    owner_id: Optional[int] = None
    allow_no_keyword: bool = False
    source: str = "manual"  # manual | capture


def create_lead(db: Session, data: dict, user: Optional[User], source: str, cfg: dict,
                is_sample: bool = False) -> tuple[Optional[Lead], Optional[dict]]:
    norm = parsing.normalize_post_url(data["post_url"])
    dup = _dup_info(db, norm)
    if dup:
        return None, dup
    text = data.get("post_text", "")
    a = parsing.analyze(text, data["post_url"], data.get("post_age_text", ""), cfg["keywords"], cfg["intent_words"])
    post_date = data.get("post_date")
    if isinstance(post_date, str):
        try:
            post_date = datetime.fromisoformat(post_date.replace("Z", "+00:00"))
        except ValueError:
            post_date = None
    if post_date is not None and post_date.tzinfo:
        post_date = post_date.astimezone(timezone.utc).replace(tzinfo=None)
    if not post_date and a["post_date"]:
        post_date = datetime.fromisoformat(a["post_date"])
    contacts = a["contacts"]
    lead = Lead(
        post_url=norm, post_text=text.strip(), author_name=(data.get("author_name") or "").strip(),
        author_headline=(data.get("author_headline") or "").strip(),
        author_url=(data.get("author_url") or "").strip(),
        keywords=a["keywords"] or [k for k in (data.get("force_keywords") or []) if k in cfg["keywords"]],
        intent=a["intent"], intent_words=a["intent_words"],
        lead_types=data.get("lead_types") if data.get("lead_types") is not None else a["lead_types"],
        vertical=data.get("vertical") if data.get("vertical") is not None else a["vertical"],
        campaign_models=data.get("campaign_models") if data.get("campaign_models") is not None else a["campaign_models"],
        geo=data.get("geo") if data.get("geo") is not None else a["geo"],
        post_age_text=a["post_age_text"], post_date=post_date, contacts=contacts,
        compliance_flag=a["compliance_flag"], compliance_terms=a["compliance_terms"],
        source=source, is_sample=is_sample, notes=data.get("notes") or "",
        added_by_id=user.id if user else None,
        owner_id=data.get("owner_id") or (user.id if user else None),
        status="New",
    )
    db.add(lead)
    db.flush()
    log_activity(db, lead.id, user, f"Lead captured via {source}")
    db.commit()
    db.refresh(lead)
    return lead, None


@app.post("/api/leads", status_code=201)
def add_lead(data: LeadIn, bg: BackgroundTasks, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not parsing.is_linkedin_url(data.post_url):
        raise HTTPException(422, "Post link must be a linkedin.com link")
    cfg = get_config(db)
    if not parsing.match_keywords(data.post_text, cfg["keywords"]) and not data.allow_no_keyword:
        raise HTTPException(422, "No tracked keyword found in this post. Save anyway?")
    src = data.source if data.source in ("manual", "capture") else "manual"
    lead, dup = create_lead(db, data.model_dump(), user, src, cfg)
    if dup:
        return JSONResponse(status_code=409, content={"detail": "Duplicate post", "duplicate": dup})
    n = create_notification(db, lead)
    bg.add_task(deliver_external, n.id)
    return {"lead": lead_dict(lead, cfg["active_days"], full=True),
            "notification": {"title": n.title, "channels": n.channels}}


def _filtered(db: Session, cfg: dict, tab: str, q: str, keyword: str, lead_type: str, status: str,
              intent: str, owner: str, source: str, user: User):
    stmt = select(Lead)
    cutoff = utcnow() - timedelta(days=cfg["active_days"])
    if tab == "new":
        stmt = stmt.where(Lead.status == "New", or_(Lead.post_date.is_(None), Lead.post_date >= cutoff))
    elif tab == "old":
        stmt = stmt.where(Lead.status == "New", Lead.post_date < cutoff)
    elif tab == "progress":
        stmt = stmt.where(Lead.status.in_(["Reviewed", "Contacted"]))
    elif tab == "history":
        stmt = stmt.where(Lead.status.in_(["Won", "Lost"]))
    if status:
        stmt = stmt.where(Lead.status == status)
    if intent:
        stmt = stmt.where(Lead.intent == intent)
    if source:
        stmt = stmt.where(Lead.source == source)
    if owner == "me":
        stmt = stmt.where(Lead.owner_id == user.id)
    elif owner.isdigit():
        stmt = stmt.where(Lead.owner_id == int(owner))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(Lead.post_text).like(like), func.lower(Lead.author_name).like(like),
                              func.lower(Lead.notes).like(like)))
    rows = db.scalars(stmt.order_by(func.coalesce(Lead.post_date, Lead.captured_at).desc(), Lead.id.desc())).unique().all()
    if keyword:
        rows = [r for r in rows if keyword.lower() in [k.lower() for k in (r.keywords or [])]]
    if lead_type:
        rows = [r for r in rows if lead_type in (r.lead_types or [])]
    return rows


@app.get("/api/leads")
def list_leads(tab: str = "new", q: str = "", keyword: str = "", lead_type: str = "", status: str = "",
               intent: str = "", owner: str = "", source: str = "", page: int = Query(1, ge=1),
               per_page: int = Query(30, ge=1, le=200),
               user: User = Depends(current_user), db: Session = Depends(get_db)):
    cfg = get_config(db)
    rows = _filtered(db, cfg, tab, q.strip(), keyword, lead_type, status, intent, owner, source, user)
    total = len(rows)
    rows = rows[(page - 1) * per_page: page * per_page]
    return {"items": [lead_dict(r, cfg["active_days"]) for r in rows], "total": total, "page": page,
            "per_page": per_page}


@app.get("/api/leads/export.csv")
def export_csv(tab: str = "all", user: User = Depends(current_user), db: Session = Depends(get_db)):
    cfg = get_config(db)
    rows = _filtered(db, cfg, tab, "", "", "", "", "", "", "", user)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "post_url", "author", "keywords", "intent", "lead_types", "vertical", "campaign_models",
                "geo", "post_age", "post_date", "status", "owner", "added_by", "source", "compliance",
                "emails", "phones", "captured_at", "notes", "post_text"])
    for r in rows:
        c = r.contacts or {}
        w.writerow([r.id, r.post_url, r.author_name, "; ".join(r.keywords or []), r.intent,
                    "; ".join(r.lead_types or []), r.vertical, "; ".join(r.campaign_models or []), r.geo,
                    parsing.human_age(r.post_date), iso(r.post_date) or "", r.status,
                    r.owner.name if r.owner else "", r.added_by.name if r.added_by else r.source, r.source,
                    "Compliance review" if r.compliance_flag else "", "; ".join(c.get("emails", [])),
                    "; ".join(c.get("phones", [])), iso(r.captured_at), r.notes, r.post_text])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=leads-{tab}.csv"})


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    cfg = get_config(db)
    acts = db.scalars(select(Activity).where(Activity.lead_id == lead_id).order_by(Activity.id.desc())).unique().all()
    return {"lead": lead_dict(lead, cfg["active_days"], full=True),
            "activity": [{"action": a.action, "user": a.user.name if a.user else "System",
                          "at": iso(a.created_at)} for a in acts]}


class LeadPatch(BaseModel):
    status: Optional[str] = None
    owner_id: Optional[int] = None
    clear_owner: bool = False
    notes: Optional[str] = None
    lead_types: Optional[list[str]] = None
    vertical: Optional[str] = None
    campaign_models: Optional[list[str]] = None
    geo: Optional[str] = None
    author_name: Optional[str] = None
    author_headline: Optional[str] = None


@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: int, data: LeadPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if data.status is not None:
        if data.status not in STATUSES:
            raise HTTPException(400, "Invalid status")
        if data.status != lead.status:
            log_activity(db, lead.id, user, f"Status {lead.status} → {data.status}")
            lead.status = data.status
            if data.status in ("Reviewed", "Contacted") and not lead.owner_id:
                lead.owner_id = user.id
    if data.clear_owner:
        lead.owner_id = None
        log_activity(db, lead.id, user, "Owner removed")
    elif data.owner_id is not None and data.owner_id != lead.owner_id:
        o = db.get(User, data.owner_id)
        if not o or not o.approved:
            raise HTTPException(400, "Invalid owner")
        lead.owner_id = o.id
        log_activity(db, lead.id, user, f"Owner set to {o.name}")
    if data.notes is not None and data.notes != lead.notes:
        lead.notes = data.notes[:5000]
        log_activity(db, lead.id, user, "Notes updated")
    for f in ("lead_types", "vertical", "campaign_models", "geo", "author_name", "author_headline"):
        v = getattr(data, f)
        if v is not None and v != getattr(lead, f):
            setattr(lead, f, v)
            if f == "lead_types":
                log_activity(db, lead.id, user, "Lead type confirmed: " + (", ".join(v) or "none"))
    lead.updated_at = utcnow()
    db.commit()
    db.refresh(lead)
    return {"lead": lead_dict(lead, get_config(db)["active_days"], full=True)}


@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    if user.role != "admin" and lead.added_by_id != user.id:
        raise HTTPException(403, "Only an admin or the person who added it can delete this lead")
    db.query(Activity).filter(Activity.lead_id == lead_id).delete()
    db.query(Notification).filter(Notification.lead_id == lead_id).delete()
    db.delete(lead)
    db.commit()
    return {"ok": True}


# ======================================================================= stats
@app.get("/api/stats")
def stats(user: User = Depends(current_user), db: Session = Depends(get_db)):
    cfg = get_config(db)
    rows = db.scalars(select(Lead)).unique().all()
    tabs = defaultdict(int)
    by_kw_won, by_type_won, by_kw_total = defaultdict(int), defaultdict(int), defaultdict(int)
    high_new = compliance = mine = today = 0
    day_ago = utcnow() - timedelta(days=1)
    for r in rows:
        t = lead_tab(r, cfg["active_days"])
        tabs[t] += 1
        if t == "new" and r.intent == "High":
            high_new += 1
        if r.compliance_flag and r.status not in ("Won", "Lost"):
            compliance += 1
        if r.owner_id == user.id and t == "progress":
            mine += 1
        if r.captured_at >= day_ago:
            today += 1
        for k in r.keywords or []:
            by_kw_total[k] += 1
            if r.status == "Won":
                by_kw_won[k] += 1
        if r.status == "Won":
            for lt in r.lead_types or []:
                by_type_won[lt] += 1
    won = sum(1 for r in rows if r.status == "Won")
    lost = sum(1 for r in rows if r.status == "Lost")
    return {"tabs": {k: tabs.get(k, 0) for k in ("new", "progress", "old", "history")}, "total": len(rows),
            "high_intent_new": high_new, "compliance_open": compliance, "my_in_progress": mine,
            "captured_24h": today, "won": won, "lost": lost,
            "win_rate": round(won * 100 / (won + lost)) if (won + lost) else None,
            "keywords": sorted([{"keyword": k, "total": v, "won": by_kw_won.get(k, 0)} for k, v in by_kw_total.items()],
                               key=lambda x: -x["total"]),
            "won_by_type": sorted([{"type": k, "won": v} for k, v in by_type_won.items()], key=lambda x: -x["won"]),
            "sample_count": sum(1 for r in rows if r.is_sample)}


# ======================================================================= notifications
@app.get("/api/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).order_by(Notification.id.desc()).limit(30)).all()
    if user.role != "admin":
        rows = [n for n in rows if n.lead_id]
    seen = db.get(NotificationRead, user.id)
    last = seen.last_seen_id if seen else 0
    return {"items": [{"id": n.id, "lead_id": n.lead_id, "title": n.title, "body": n.body,
                       "channels": n.channels, "at": iso(n.created_at), "unread": n.id > last} for n in rows],
            "unread": sum(1 for n in rows if n.id > last)}


@app.post("/api/notifications/seen")
def notifications_seen(user: User = Depends(current_user), db: Session = Depends(get_db)):
    top = db.scalar(select(func.max(Notification.id))) or 0
    row = db.get(NotificationRead, user.id)
    if row:
        row.last_seen_id = top
    else:
        db.add(NotificationRead(user_id=user.id, last_seen_id=top))
    db.commit()
    return {"ok": True}


# ======================================================================= team
@app.get("/api/users")
def users(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).order_by(User.approved, User.name)).all()
    if user.role != "admin":
        return {"items": [user_public(u) for u in rows if u.approved and u.active]}
    return {"items": [user_full(u) for u in rows]}


class UserPatch(BaseModel):
    approved: Optional[bool] = None
    role: Optional[str] = None
    active: Optional[bool] = None


@app.patch("/api/users/{user_id}")
def update_user(user_id: int, data: UserPatch, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id and (data.role == "member" or data.active is False):
        raise HTTPException(400, "You can't demote or deactivate yourself")
    if data.approved is not None:
        u.approved = data.approved
    if data.role in ("admin", "member"):
        u.role = data.role
    if data.active is not None:
        u.active = data.active
    db.commit()
    return {"user": user_full(u)}


# ======================================================================= sample data (demo)
SAMPLE_POSTS = [
    ("Sample · Riya Sharma (demo)", "Affiliate Manager · Demo Network", "3h",
     "We are LIVE with a new BFSI campaign 🚀 Credit card + personal loan offers, CPL & CPA payouts. "
     "Looking for affiliate marketing partners and publishers with quality traffic. GEO: India. "
     "DM me or mail partners@example.com #affiliatemarketing #performancemarketing"),
    ("Sample · Arjun Mehta (demo)", "Founder · D2C Beauty Brand", "1d",
     "Need an agency for Meta Ads and influencer marketing for our skincare launch. Performance marketing "
     "experience in beauty preferred. Can anyone recommend? Budget is ready. Reach out: +91 98765 43210"),
    ("Sample · Neha Kapoor (demo)", "Partnerships · Demo Fintech", "2d",
     "Onboarding vendors for our Demat account opening project 📈 CPA model, pan-India. Affiliate marketing "
     "agencies and vendors with BFSI experience, please connect. vendors@example.com"),
    ("Sample · Kabir Singh (demo)", "BD Head · Demo Media", "5h",
     "Our network is looking for direct advertisers and direct campaigns for app installs (CPI) and CPS offers. "
     "Performance marketing team ready with Tier 1 + India traffic. Let's connect."),
    ("Sample · Aisha Khan (demo)", "Agency Owner · Demo Digital", "4d",
     "Hiring partners who can bring client projects! We are a performance marketing agency, looking for "
     "channel partners for affiliate marketing projects. RevShare available. wa.me/919800000000"),
    ("Sample · Vikram Rao (demo)", "Growth · Demo Gaming", "6h",
     "Seeking affiliate partners for our iGaming / sportsbook campaign. CPA + RevShare, GEO: LATAM, India. "
     "USDT payouts weekly. DM for details."),
    ("Sample · Sana Iqbal (demo)", "Marketing Lead · Demo EdTech", "2mo",
     "Looking for affiliate marketing partners for our course launch. CPL model, India. Contact: hello@example.com"),
    ("Sample · Rohan Das (demo)", "Affiliate Lead · Demo Insurance", "3w",
     "Performance marketing publishers needed for health insurance leads. CPL payouts, GEO: India. Inviting partners."),
]


@app.post("/api/admin/sample")
def add_samples(bg: BackgroundTasks, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    cfg = get_config(db)
    created = 0
    for i, (name, headline, age, text) in enumerate(SAMPLE_POSTS):
        url = f"https://www.linkedin.com/posts/sample-demo-post-{i + 1}-activity-demo{i + 1}/"
        lead, dup = create_lead(db, {"post_url": url, "post_text": text, "author_name": name,
                                     "author_headline": headline, "post_age_text": age}, admin, "sample", cfg,
                                is_sample=True)
        if lead:
            created += 1
            if i == 0:
                create_notification(db, lead)
    return {"created": created}


@app.delete("/api/admin/sample")
def clear_samples(admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    ids = [r for r in db.scalars(select(Lead.id).where(Lead.is_sample.is_(True))).all()]
    if ids:
        db.query(Activity).filter(Activity.lead_id.in_(ids)).delete(synchronize_session=False)
        db.query(Notification).filter(Notification.lead_id.in_(ids)).delete(synchronize_session=False)
        db.query(Lead).filter(Lead.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    return {"deleted": len(ids)}


# ======================================================================= auto-discovery
_discovery_lock = threading.Lock()


def _save_discovery_status(db: Session, stats: dict) -> None:
    row = db.get(AppSetting, "discovery_status")
    if row:
        row.value = stats
    else:
        db.add(AppSetting(key="discovery_status", value=stats))
    db.commit()


def _run_discovery() -> dict:
    if not _discovery_lock.acquire(blocking=False):
        return {"errors": ["A discovery run is already in progress"]}
    try:
        return discovery.run_discovery(get_config, create_lead, create_notification, deliver_external,
                                       _save_discovery_status)
    finally:
        _discovery_lock.release()


@app.get("/api/discovery")
def discovery_status(user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.get(AppSetting, "discovery_status")
    cfg = get_config(db)
    return {"provider": discovery.provider_name(), "enabled": cfg.get("discovery_enabled", True),
            "interval_min": cfg.get("discovery_interval_min", 60), "window": cfg.get("discovery_window", "w"),
            "running": _discovery_lock.locked(), "last": row.value if row else None}


@app.post("/api/discovery/run")
async def discovery_run(admin: User = Depends(admin_user)):
    if not discovery.provider_name():
        raise HTTPException(400, "Add SERPER_API_KEY (or SERPAPI_API_KEY) on the server to turn on auto-discovery")
    stats = await asyncio.get_running_loop().run_in_executor(None, _run_discovery)
    return stats


@app.get("/api/keywords/suggestions")
def keyword_suggestions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    cfg = get_config(db)
    texts = [t for (t,) in db.execute(select(Lead.post_text).where(Lead.is_sample.is_(False))
                                      .order_by(Lead.id.desc()).limit(500)).all()]
    return {"items": discovery.suggest_keywords(texts, cfg["keywords"])}


# ======================================================================= vendor webhook
def _pick(d: dict, *keys: str) -> Any:
    for k in keys:
        cur: Any = d
        for part in k.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur not in (None, ""):
            return cur
    return None


@app.post("/api/webhook/ingest")
async def webhook_ingest(request: Request, bg: BackgroundTasks, db: Session = Depends(get_db),
                         x_webhook_secret: str = Header(default="")):
    if not settings.WEBHOOK_SECRET:
        raise HTTPException(503, "Webhook disabled: set WEBHOOK_SECRET")
    if not secrets.compare_digest(x_webhook_secret, settings.WEBHOOK_SECRET):
        raise HTTPException(401, "Bad webhook secret")
    try:
        payload = await request.json()
    except ValueError:
        raise HTTPException(400, "Body must be JSON")
    items = payload
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("data") or payload.get("mentions") or [payload]
        if isinstance(items, dict):
            items = [items]
    if not isinstance(items, list):
        raise HTTPException(400, "Expected an object or a list")
    cfg = get_config(db)
    result = {"created": 0, "duplicates": 0, "ignored_no_keyword": 0, "invalid": 0}
    for it in items[:200]:
        if not isinstance(it, dict):
            result["invalid"] += 1
            continue
        url = _pick(it, "post_url", "url", "link", "permalink", "postUrl")
        text = _pick(it, "post_text", "text", "content", "body", "postText", "title") or ""
        if not url or not text:
            result["invalid"] += 1
            continue
        if not parsing.match_keywords(str(text), cfg["keywords"]):
            result["ignored_no_keyword"] += 1
            continue
        data = {"post_url": str(url), "post_text": str(text),
                "author_name": str(_pick(it, "author_name", "author.name", "authorName", "author") or "")[:200],
                "author_url": str(_pick(it, "author_url", "author.url", "authorUrl", "author.profile_url") or "")[:600],
                "author_headline": str(_pick(it, "author_headline", "author.headline", "authorHeadline") or "")[:300],
                "post_date": _pick(it, "posted_at", "published_at", "timestamp", "created_at", "date")}
        lead, dup = create_lead(db, data, None, "webhook", cfg)
        if dup:
            result["duplicates"] += 1
            continue
        result["created"] += 1
        n = create_notification(db, lead)
        bg.add_task(deliver_external, n.id)
    return result


# ======================================================================= frontend
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return FileResponse(STATIC / "sw.js", media_type="application/javascript")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        detail = getattr(exc, "detail", "Not found")
        return JSONResponse({"detail": detail}, status_code=404)
    return FileResponse(STATIC / "index.html")
