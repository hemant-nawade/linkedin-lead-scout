"""Auto-discovery with a fake search provider (no network, no LinkedIn)."""
import os
import time

os.environ["DATABASE_URL"] = "sqlite:///./data/test_discovery.db"
os.environ["SERPER_API_KEY"] = "fake"

from fastapi.testclient import TestClient  # noqa: E402

from app import discovery  # noqa: E402

now = int(time.time() * 1000)
aid = lambda h: str((now - h * 3600 * 1000) << 22)  # noqa: E731
FAKE = [
    {"url": f"https://www.linkedin.com/posts/demo-user_x-activity-{aid(5)}-Ab", "title": "Demo User on LinkedIn: Looking for traffic partners",
     "snippet": "Affiliate marketing campaigns live, CPA. GEO: India", "date_text": "5 hours ago"},
    {"url": f"https://www.linkedin.com/posts/old-user_x-activity-{aid(24 * 90)}-Cd", "title": "Old post", "snippet": "affiliate marketing", "date_text": ""},
    {"url": "https://www.linkedin.com/jobs/view/1", "title": "Job", "snippet": "affiliate marketing", "date_text": ""},
]


def test_discovery_creates_dedupes_and_skips(monkeypatch):
    if os.path.exists("data/test_discovery.db"):
        os.remove("data/test_discovery.db")
    monkeypatch.setattr(discovery, "search", lambda kw, *a, **k: FAKE if kw == "affiliate marketing" else [])
    from app.main import app
    with TestClient(app) as c:
        c.post("/api/auth/signup", json={"name": "Admin", "email": "a@example.com", "password": "password123"})
        r = c.post("/api/discovery/run").json()
        assert r["created"] == 1 and r["skipped_old"] == 1 and r["skipped_other"] == 1
        assert c.post("/api/discovery/run").json()["created"] == 0
        lead = c.get("/api/leads?tab=new").json()["items"][0]
        assert lead["author_name"] == "Demo User" and lead["source"] == "search"
        assert lead["embed_url"].startswith("https://www.linkedin.com/embed/feed/update/urn:li:activity:")
        assert c.get("/api/keywords/suggestions").json()["items"]


def test_profile_link_and_export(monkeypatch):
    from app import parsing
    assert parsing.profile_from_post_url(
        "https://www.linkedin.com/posts/pragati-thapa-12ab34_finance-activity-7400000000000000000-x") == \
        "https://www.linkedin.com/in/pragati-thapa-12ab34/"
    from app.main import app
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"email": "a@example.com", "password": "password123"})
        csv_text = c.get("/api/leads/export.csv?keyword=affiliate%20marketing").text
        assert "Profile link" in csv_text and "https://www.linkedin.com/in/demo-user/" in csv_text
