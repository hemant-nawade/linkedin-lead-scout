"""Email/password accounts + signed session cookie + role checks."""
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

COOKIE = "ls_session"
_ser = URLSafeTimedSerializer(settings.SECRET_KEY, salt="ls-session")


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt(rounds=12)).decode()


def verify_password(pw: str, hashed: Optional[str]) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except ValueError:
        return False


def set_session(resp: Response, user: User) -> None:
    token = _ser.dumps({"uid": user.id, "ph": (user.password_hash or "")[-10:]})
    resp.set_cookie(COOKIE, token, max_age=settings.SESSION_DAYS * 86400, httponly=True,
                    samesite="lax", secure=settings.COOKIE_SECURE, path="/")


def clear_session(resp: Response) -> None:
    resp.delete_cookie(COOKIE, path="/")


def _user_from_request(request: Request, db: Session) -> Optional[User]:
    tok = request.cookies.get(COOKIE)
    if not tok:
        return None
    try:
        data = _ser.loads(tok, max_age=settings.SESSION_DAYS * 86400)
    except (BadSignature, SignatureExpired):
        return None
    user = db.get(User, data.get("uid"))
    if not user or not user.active:
        return None
    # Changing password invalidates old sessions
    if data.get("ph") != (user.password_hash or "")[-10:]:
        return None
    return user


def optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    return _user_from_request(request, db)


def any_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Logged in (may still be pending approval)."""
    user = _user_from_request(request, db)
    if not user:
        raise HTTPException(401, "Please log in")
    return user


def current_user(user: User = Depends(any_user)) -> User:
    if not user.approved:
        raise HTTPException(403, "Your account is waiting for admin approval")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin only")
    return user
