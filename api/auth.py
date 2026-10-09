import os

import bcrypt
from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer


def signer() -> URLSafeTimedSerializer:
    secret = os.getenv("SESSION_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("SESSION_SECRET must contain at least 32 characters")
    return URLSafeTimedSerializer(secret, salt="dcbot-session")


def check_password(username: str, password: str) -> bool:
    expected = os.getenv("DASHBOARD_USER", "")
    password_hash = os.getenv("DASHBOARD_PASSWORD_HASH", "")
    if not expected or not password_hash or username != expected:
        return False
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def require_session(request: Request) -> str:
    cookie = request.cookies.get("dcbot_session", "")
    try:
        username = signer().loads(cookie, max_age=86400)
    except BadSignature as exc:
        raise HTTPException(status_code=401, detail="Authentication required") from exc
    if username != os.getenv("DASHBOARD_USER"):
        raise HTTPException(status_code=401, detail="Authentication required")
    return username
