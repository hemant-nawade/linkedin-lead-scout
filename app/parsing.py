"""Text intelligence: keyword match, intent tag, lead type, vertical, campaign model,
GEO, contacts, post age, URL normalisation. Pure functions — easy to test."""
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

# ---------------------------------------------------------------- defaults
DEFAULT_KEYWORDS = [
    "affiliate marketing",
    "affiliate marketing projects",
    "affiliate",
    "performance marketing",
    "RTDS",
]

DEFAULT_INTENT_WORDS = [
    "looking for", "need agency", "need an agency", "hiring", "recommend", "seeking",
    "searching for", "in search of", "need partners", "partners needed", "publishers needed",
    "looking to onboard", "want to onboard", "dm me", "dm for", "reach out", "connect with me",
    "inviting", "open for", "required", "requirement", "actively looking", "looking to connect",
    "looking to partner", "looking to collaborate", "opening new partner", "partner spots", "let's connect",
    "feel free to dm", "dm us", "who can bring", "who can help",
]

LEAD_TYPE_RULES = {
    "Partner/publisher chahiye": [
        "publisher", "publishers", "traffic partner", "execution partner", "affiliate partner",
        "traffic source", "media buyer", "partners needed", "looking for partners", "need partners",
        "run campaign", "running campaign", "live campaign", "campaign is live", "campaign live",
        "traffic partners", "quality traffic", "affiliate networks", "cpa networks", "direct publishers",
        "sub-publishers", "execution vendors", "execution partners", "affiliate partners", "media buyers",
        "available campaigns", "campaigns available", "traffic",
    ],
    "Advertiser chahiye": [
        "advertiser", "advertisers", "direct campaign", "direct campaigns", "direct offers",
        "looking for brands", "brands looking", "direct clients", "offers wanted", "need offers",
        "direct advertisers", "brand partnerships", "active campaigns", "looking for campaigns",
        "looking for active", "direct campaigns only", "advertisers and direct agencies",
    ],
    "Agency chahiye": [
        "need agency", "need an agency", "looking for an agency", "looking for agency",
        "meta ads", "facebook ads", "google ads agency", "influencer agency",
        "influencer marketing agency", "ads agency", "marketing agency",
    ],
    "Vendor onboarding": [
        "vendor", "vendors", "onboard", "onboarding", "empanel", "demat",
    ],
    "Client projects chahiye": [
        "client projects", "bring projects", "bring clients", "get projects", "projects",
        "channel partner", "referral partner", "partners who can bring", "provide us with client projects",
        "access to potential clients", "bring in projects",
    ],
}

VERTICAL_RULES = {
    "BFSI": ["bfsi", "bank", "banking", "loan", "credit card", "demat", "insurance", "mutual fund",
             "fintech", "trading account", "personal loan", "upi", "savings account", "angel one",
             "upstox", "motilal", "finance", "loans"],
    "Crypto": ["crypto", "cryptocurrency", "bitcoin", "usdt", "web3", "bybit", "wazirx", "binance"],
    "iGaming": ["igaming", "i-gaming", "casino", "betting", "sportsbook", "gambling", "fantasy", "linebet", "sports betting"],
    "Forex": ["forex", "fx broker", "cfd", "exness", "iforex"],
    "Beauty": ["beauty", "skincare", "cosmetic", "makeup"],
    "E-commerce": ["ecommerce", "e-commerce", "d2c", "shopify", "marketplace", "meesho", "zalora", "shopping"],
    "EdTech": ["edtech", "course", "education", "students"],
    "Health": ["health", "pharma", "wellness", "nutra", "nutraceutical"],
    "Apps/Gaming": ["app install", "mobile game", "gaming app", "cpi", "android & ios", "mobile app"],
    "Real estate": ["real estate", "property", "realty"],
    "Travel": ["travel", "hotel", "flight"],
}

COMPLIANCE_TERMS = ["igaming", "i-gaming", "betting", "casino", "gambling", "sportsbook",
                    "crypto", "cryptocurrency", "forex", "usdt", "linebet", "bybit", "wazirx", "exness", "iforex"]

CAMPAIGN_MODEL_RE = re.compile(
    r"\b(CPA|CPL|CPI|CPS|CPE|CPC|CPM|CPR|CPO|CPV|Rev\s?Share|Revenue\s?Share)\b", re.I)

GEO_TERMS = [
    "India", "USA", "US", "UK", "UAE", "GCC", "KSA", "Saudi", "LATAM", "Brazil", "Mexico",
    "Indonesia", "Philippines", "Vietnam", "Thailand", "Malaysia", "Bangladesh", "Pakistan",
    "Nepal", "Sri Lanka", "Nigeria", "Kenya", "South Africa", "Europe", "EU", "Canada",
    "Australia", "Tier 1", "Tier-1", "Tier 2", "Global", "Worldwide", "APAC", "MENA", "SEA",
]

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\w/])(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3,5}[\s-]?\d{4,6}(?![\w/])")
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
WA_RE = re.compile(r"(?:https?://)?(?:wa\.me|api\.whatsapp\.com|chat\.whatsapp\.com)/[^\s<>\"')]+", re.I)


def _has(text_l: str, term: str) -> bool:
    t = term.lower().strip()
    if not t:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", text_l) is not None


def match_keywords(text: str, keywords: list[str]) -> list[str]:
    tl = (text or "").lower()
    found = [k for k in keywords if _has(tl, k)]
    # Keep the most specific: drop "affiliate" if "affiliate marketing" matched
    found = [k for k in found if not any(o != k and k.lower() in o.lower() for o in found)]
    return found


def detect_intent(text: str, intent_words: list[str]) -> tuple[str, list[str]]:
    tl = (text or "").lower()
    hits = [w for w in intent_words if _has(tl, w)]
    return ("High" if hits else "Normal"), hits


def detect_lead_types(text: str) -> list[str]:
    tl = (text or "").lower()
    scored = []
    for lt, terms in LEAD_TYPE_RULES.items():
        n = sum(1 for t in terms if _has(tl, t))
        if n:
            scored.append((n, lt))
    scored.sort(reverse=True)
    return [lt for _, lt in scored[:2]]


def detect_vertical(text: str) -> str:
    tl = (text or "").lower()
    best, best_n = "", 0
    for v, terms in VERTICAL_RULES.items():
        n = sum(1 for t in terms if _has(tl, t))
        if n > best_n:
            best, best_n = v, n
    return best


def detect_campaign_models(text: str) -> list[str]:
    out = []
    for m in CAMPAIGN_MODEL_RE.findall(text or ""):
        m = m.upper().replace(" ", "")
        if m.startswith("REV"):
            m = "RevShare"
        if m not in out:
            out.append(m)
    return out


def detect_geo(text: str) -> str:
    t = text or ""
    m = re.search(r"\bGEOs?\s*[:\-–]\s*([A-Za-z][A-Za-z0-9 ,/+&|-]{1,60})", t, re.I)
    if m:
        val = re.split(r"\s+(?:DM|dm|Dm|contact|Contact|mail|email|call|payouts?|Payouts?|with|for|USDT|CPA|CPL|CPI|CPS)\b",
                       m.group(1))[0]
        val = re.sub(r"\s*\|\s*", ", ", val).strip(" .,-|")
        if val:
            return val
    found = []
    for g in GEO_TERMS:
        if re.search(r"(?<![A-Za-z])" + re.escape(g) + r"(?![A-Za-z])", t):
            if g == "US" and "USDT" in t and not re.search(r"\bUS\b(?!DT)", t):
                continue
            found.append(g)
    return ", ".join(dict.fromkeys(found))[:120]


def detect_compliance(text: str) -> list[str]:
    tl = (text or "").lower()
    return [t for t in COMPLIANCE_TERMS if _has(tl, t)]


def extract_contacts(text: str) -> dict:
    t = text or ""
    emails = list(dict.fromkeys(EMAIL_RE.findall(t)))
    whatsapp = list(dict.fromkeys(WA_RE.findall(t)))
    links = [u.rstrip(".,") for u in URL_RE.findall(t)]
    links = [u for u in dict.fromkeys(links) if "linkedin.com/feed/hashtag" not in u]
    phones = []
    no_urls = URL_RE.sub(" ", WA_RE.sub(" ", t))
    for p in PHONE_RE.findall(no_urls):
        digits = re.sub(r"\D", "", p)
        if 10 <= len(digits) <= 13 and not ACTIVITY_RE.search(p):
            phones.append(p.strip())
    phones = list(dict.fromkeys(phones))
    return {"emails": emails, "phones": phones, "whatsapp": whatsapp, "links": links}


# ---------------------------------------------------------------- age / date
AGE_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d{1,3})\s*(s|m|min|mins|h|hr|hrs|d|w|wk|mo|mos|y|yr|yrs|"
    r"seconds?|minutes?|hours?|days?|weeks?|months?|years?)(?:\s+ago)?(?![A-Za-z])",
    re.I)


def parse_age(age_text: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """'3h', '5d', '2mo', '1yr', '2 weeks ago' -> approximate post datetime (UTC naive)."""
    if not age_text:
        return None
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    s = age_text.strip().lower()
    if s in ("now", "just now"):
        return now
    m = AGE_RE.search(s)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    if unit in ("s",) or unit.startswith("second"):
        delta = timedelta(seconds=n)
    elif unit in ("m", "min", "mins") or unit.startswith("minute"):
        delta = timedelta(minutes=n)
    elif unit in ("h", "hr", "hrs") or unit.startswith("hour"):
        delta = timedelta(hours=n)
    elif unit == "d" or unit.startswith("day"):
        delta = timedelta(days=n)
    elif unit in ("w", "wk") or unit.startswith("week"):
        delta = timedelta(weeks=n)
    elif unit in ("mo", "mos") or unit.startswith("month"):
        delta = timedelta(days=30 * n)
    else:
        delta = timedelta(days=365 * n)
    return now - delta


def find_age_token(text: str) -> str:
    """Look for LinkedIn's '3h •' / '5d' marker near the top of pasted post text."""
    head = "\n".join((text or "").splitlines()[:8])
    m = re.search(r"(?<![A-Za-z0-9])(\d{1,3}\s?(?:h|d|w|mo|yr|m))\s*•", head)
    if m:
        return m.group(1).replace(" ", "")
    return ""


def human_age(dt: Optional[datetime], now: Optional[datetime] = None) -> str:
    if not dt:
        return "Date unknown"
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    sec = max(0, (now - dt).total_seconds())
    if sec < 3600:
        return f"{int(sec // 60) or 1}m"
    if sec < 86400:
        return f"{int(sec // 3600)}h"
    days = int(sec // 86400)
    if days < 7:
        return f"{days}d"
    if days < 30:
        return f"{days // 7}w"
    if days < 365:
        return f"{days // 30}mo"
    return f"{days // 365}yr"


# ---------------------------------------------------------------- URLs
ACTIVITY_RE = re.compile(r"(?:urn:li:|urn%3Ali%3A)?(activity|share|ugcPost)(?::|%3A|-)(\d{15,22})", re.I)


def linkedin_post_id(url: str) -> Optional[tuple[str, str]]:
    m = ACTIVITY_RE.search(url or "")
    if not m:
        return None
    kind = m.group(1)
    kind = {"activity": "activity", "share": "share", "ugcpost": "ugcPost"}[kind.lower()]
    return kind, m.group(2)


def date_from_post_id(post_id: str) -> Optional[datetime]:
    """LinkedIn post IDs embed the creation time: first 41 bits = ms since epoch."""
    try:
        ms = int(post_id) >> 22
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(tzinfo=None)
        if datetime(2010, 1, 1) < dt < datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1):
            return dt
    except (ValueError, OverflowError, OSError):
        pass
    return None


def normalize_post_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    pid = linkedin_post_id(url)
    if pid and "linkedin.com" in url.lower():
        kind, num = pid
        return f"https://www.linkedin.com/feed/update/urn:li:{kind}:{num}/"
    p = urlparse(url)
    host = p.netloc.lower().replace("m.linkedin.com", "www.linkedin.com")
    if host == "linkedin.com":
        host = "www.linkedin.com"
    path = p.path.rstrip("/")
    return f"https://{host}{path}/" if path else f"https://{host}/"


def is_linkedin_url(url: str) -> bool:
    try:
        h = urlparse(url if "://" in url else "https://" + url).netloc.lower()
        return h == "linkedin.com" or h.endswith(".linkedin.com") or h == "lnkd.in"
    except ValueError:
        return False


# ---------------------------------------------------------------- one-shot analysis
def analyze(text: str, url: str = "", age_text: str = "", keywords=None, intent_words=None) -> dict:
    keywords = keywords or DEFAULT_KEYWORDS
    intent_words = intent_words or DEFAULT_INTENT_WORDS
    intent, intent_hits = detect_intent(text, intent_words)
    age_text = (age_text or "").strip() or find_age_token(text)
    post_date, date_source = None, ""
    pid = linkedin_post_id(url)
    if pid:
        post_date = date_from_post_id(pid[1])
        date_source = "link" if post_date else ""
    if not post_date and age_text:
        post_date = parse_age(age_text)
        date_source = "age" if post_date else ""
    compliance = detect_compliance(text)
    return {
        "keywords": match_keywords(text, keywords),
        "intent": intent,
        "intent_words": intent_hits,
        "lead_types": detect_lead_types(text),
        "vertical": detect_vertical(text),
        "campaign_models": detect_campaign_models(text),
        "geo": detect_geo(text),
        "contacts": extract_contacts(text),
        "compliance_flag": bool(compliance),
        "compliance_terms": compliance,
        "post_age_text": age_text,
        "post_date": post_date.isoformat() if post_date else None,
        "post_date_source": date_source,
        "normalized_url": normalize_post_url(url) if url else "",
    }
