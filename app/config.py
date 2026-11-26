"""App configuration — everything secret comes from environment variables."""
import os
import secrets


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


class Settings:
    APP_NAME = _env("APP_NAME", "LinkedIn Lead Scout")
    # Public base URL, e.g. https://leadscout.yourcompany.com (used for LinkedIn redirect + links in alerts)
    BASE_URL = _env("BASE_URL", "http://localhost:8000").rstrip("/")

    # Database: SQLite locally, Postgres in production (postgresql+psycopg://user:pass@host/db)
    DATABASE_URL = _env("DATABASE_URL", "sqlite:///./data/leadscout.db")

    # Session signing secret — MUST be set in production
    SECRET_KEY = _env("SECRET_KEY") or secrets.token_urlsafe(48)
    SESSION_DAYS = int(_env("SESSION_DAYS", "7") or 7)
    COOKIE_SECURE = BASE_URL.startswith("https://")

    # Sign In with LinkedIn using OpenID Connect (scopes: openid profile email)
    LINKEDIN_CLIENT_ID = _env("LINKEDIN_CLIENT_ID")
    LINKEDIN_CLIENT_SECRET = _env("LINKEDIN_CLIENT_SECRET")
    LINKEDIN_REDIRECT_URI = _env("LINKEDIN_REDIRECT_URI") or f"{BASE_URL}/auth/linkedin/callback"

    # Alerts
    TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = _env("TELEGRAM_CHAT_ID")
    SLACK_WEBHOOK_URL = _env("SLACK_WEBHOOK_URL")

    # Vendor webhook (Octolens or any listening tool) — header X-Webhook-Secret
    WEBHOOK_SECRET = _env("WEBHOOK_SECRET")

    # Optional bootstrap admin (created on first start if no users exist)
    ADMIN_EMAIL = _env("ADMIN_EMAIL").lower()
    ADMIN_PASSWORD = _env("ADMIN_PASSWORD")
    ADMIN_NAME = _env("ADMIN_NAME", "Admin")

    @property
    def linkedin_enabled(self) -> bool:
        return bool(self.LINKEDIN_CLIENT_ID and self.LINKEDIN_CLIENT_SECRET)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.TELEGRAM_BOT_TOKEN and self.TELEGRAM_CHAT_ID)

    @property
    def slack_enabled(self) -> bool:
        return bool(self.SLACK_WEBHOOK_URL)


settings = Settings()
