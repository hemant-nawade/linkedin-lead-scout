"""Scout-session capture API (what scout_session.py calls when you press Enter)."""
import os
import time

os.environ["DATABASE_URL"] = "sqlite:///./data/test_session.db"

from fastapi.testclient import TestClient  # noqa: E402

aid = str((int(time.time() * 1000) - 3600 * 1000) << 22)


def test_capture_flow():
    if os.path.exists("data/test_session.db"):
        os.remove("data/test_session.db")
    from app.main import app
    with TestClient(app) as c:
        c.post("/api/auth/signup", json={"name": "Riya Admin", "email": "r@example.com", "password": "password123"})
        # another test may have created the first (admin) user in this process's DB: approve ours directly
        from app.db import SessionLocal
        from app.models import User
        with SessionLocal() as db:
            u = db.query(User).filter_by(email="r@example.com").one()
            u.approved = True
            db.commit()
        c.post("/api/auth/login", json={"email": "r@example.com", "password": "password123"})
        tok = c.post("/api/me/scout-token").json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        post = {"site": "linkedin", "url": f"https://www.linkedin.com/feed/update/urn:li:activity:{aid}/",
                "page_type": "post", "title": "(3) Demo Person on LinkedIn: Looking for traffic partners | LinkedIn",
                "text": "Demo Person\nAffiliate Manager\n1h •\nLooking for affiliate marketing partners. CPA. GEO: India. mail d@example.com",
                "tag": "affiliate", "captured_by": "riya"}
        r = c.post("/api/captures", json=post, headers=h).json()
        assert r["status"] == "created" and "affiliate marketing" in r["keywords"] and r["intent"] == "High"
        assert c.post("/api/captures", json=post, headers=h).json()["status"] == "duplicate"
        person = {"site": "linkedin", "url": "https://www.linkedin.com/in/demo-founder/", "page_type": "person",
                  "title": "Demo Founder | LinkedIn", "text": "Demo Founder\nFounder at Demo Media · Pune\nAbout: performance marketing agency"}
        r2 = c.post("/api/captures", json=person, headers=h).json()
        assert r2["status"] == "created" and r2["page_type"] == "person"
        assert c.post("/api/captures", json=person, headers={"Authorization": "Bearer nope"}).status_code == 401
        lead = c.get(f"/api/leads/{r2['lead_id']}").json()["lead"]
        assert lead["author_name"] == "Demo Founder" and lead["source"] == "session" and lead["age_label"].startswith("captured")
        t = c.get("/api/session/today").json()
        assert t["mine"]["linkedin"] == 2 and t["by_site"]["linkedin"] == 2
        assert c.get("/scout/scout_session.py").status_code == 200


def test_migration_adds_columns(tmp_path):
    import sqlalchemy as sa
    from app import main
    eng = sa.create_engine(f"sqlite:///{tmp_path}/old.db")
    with eng.begin() as conn:
        conn.execute(sa.text("CREATE TABLE leads (id INTEGER PRIMARY KEY, post_url VARCHAR)"))
    old = main.engine
    main.engine = eng
    try:
        main._migrate()
    finally:
        main.engine = old
    cols = {c["name"] for c in sa.inspect(eng).get_columns("leads")}
    assert {"site", "page_type", "tag"} <= cols
