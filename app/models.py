from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="member")  # admin | member
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Sign In with LinkedIn (OIDC) — only basic profile, never password/cookie
    linkedin_sub: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    linkedin_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    linkedin_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    linkedin_picture: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    capture_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_url: Mapped[str] = mapped_column(String(600), unique=True, index=True)  # normalized
    author_name: Mapped[str] = mapped_column(String(200), default="")
    author_headline: Mapped[str] = mapped_column(String(300), default="")
    author_url: Mapped[str] = mapped_column(String(600), default="")
    post_text: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    intent: Mapped[str] = mapped_column(String(10), default="Normal")  # High | Normal
    intent_words: Mapped[list] = mapped_column(JSON, default=list)
    lead_types: Mapped[list] = mapped_column(JSON, default=list)
    vertical: Mapped[str] = mapped_column(String(80), default="")
    campaign_models: Mapped[list] = mapped_column(JSON, default=list)
    geo: Mapped[str] = mapped_column(String(120), default="")
    post_age_text: Mapped[str] = mapped_column(String(20), default="")
    post_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    contacts: Mapped[dict] = mapped_column(JSON, default=dict)  # emails, phones, links
    compliance_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    compliance_terms: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(30), default="manual")  # manual|capture|webhook|sample|search|session
    site: Mapped[str] = mapped_column(String(30), default="linkedin")    # linkedin|indiamart|tradeindia|web
    page_type: Mapped[str] = mapped_column(String(20), default="post")   # post|person|company|product|job|page
    tag: Mapped[str] = mapped_column(String(80), default="")             # campaign tag from scout session
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="New", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    added_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    added_by = relationship("User", foreign_keys=[added_by_id], lazy="joined")
    owner = relationship("User", foreign_keys=[owner_id], lazy="joined")


class Activity(Base):
    __tablename__ = "activity"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    user = relationship("User", lazy="joined")


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[Optional[int]] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    channels: Mapped[dict] = mapped_column(JSON, default=dict)  # {"in_app": "sent", "telegram": "sent|failed|off"}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class NotificationRead(Base):
    __tablename__ = "notification_reads"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    last_seen_id: Mapped[int] = mapped_column(Integer, default=0)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
