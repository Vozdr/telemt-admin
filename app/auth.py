from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from settings import (
    BASIC_ADMIN_PASS,
    BASIC_ADMIN_USER,
    ENABLE_BASIC_AUTH,
    ENABLE_WEB_AUTH,
    SESSION_SECRET,
    WEB_ADMIN_USER,
)


security = HTTPBasic(auto_error=False)


def make_session_token(username: str) -> str:
    issued = str(int(time.time()))
    payload = f"{username}:{issued}"
    signature = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()


def valid_session_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        username, issued, signature = raw.rsplit(":", 2)
    except Exception:
        return False
    payload = f"{username}:{issued}"
    expected = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    if username != WEB_ADMIN_USER:
        return False
    return int(time.time()) - int(issued) < 60 * 60 * 24 * 30


def valid_basic(credentials: HTTPBasicCredentials | None) -> bool:
    if not credentials:
        return False
    user_ok = secrets.compare_digest(credentials.username, BASIC_ADMIN_USER)
    pass_ok = secrets.compare_digest(credentials.password, BASIC_ADMIN_PASS)
    return user_ok and pass_ok


def require_auth(
    credentials: HTTPBasicCredentials | None = Depends(security),
    telemt_admin_session: str | None = Cookie(default=None),
) -> None:
    if not ENABLE_BASIC_AUTH and not ENABLE_WEB_AUTH:
        return
    if ENABLE_BASIC_AUTH and not valid_basic(credentials):
        raise HTTPException(
            status_code=401,
            detail="Basic authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    if ENABLE_WEB_AUTH and not valid_session_token(telemt_admin_session):
        raise HTTPException(status_code=401, detail="Web authentication required")
