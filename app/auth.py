from __future__ import annotations

import datetime as dt
import time
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from itsdangerous import BadSignature, URLSafeSerializer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from . import models


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
http_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _get_serializer() -> URLSafeSerializer:
    settings = get_settings()
    if not settings.session_secret:
        raise RuntimeError("SESSION_SECRET not configured")
    return URLSafeSerializer(settings.session_secret, salt="url-registry-session")


def create_session_token(user_id: int) -> str:
    serializer = _get_serializer()
    payload = {"user_id": user_id, "issued_at": time.time()}
    return serializer.dumps(payload)


def decode_session_token(token: str) -> Optional[int]:
    serializer = _get_serializer()
    try:
        data = serializer.loads(token)
    except BadSignature:
        return None
    if not isinstance(data, dict):
        return None
    issued_at = data.get("issued_at")
    if not isinstance(issued_at, (int, float)) or not 0 <= time.time() - issued_at <= 8 * 3600:
        return None
    return data.get("user_id")


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[models.User]:
    settings = get_settings()
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        return None
    user_id = decode_session_token(cookie)
    if not user_id:
        return None
    return db.get(models.User, user_id)


async def require_login(user: models.User | None = Depends(get_current_user)) -> models.User:
    if not user:
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/admin/login"})
    return user


async def require_admin(user: models.User = Depends(require_login)) -> models.User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


async def require_api_token(credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer)) -> None:
    settings = get_settings()
    if not settings.api_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="API token not configured")
    if credentials is None or credentials.scheme.lower() != "bearer" or not secrets.compare_digest(credentials.credentials, settings.api_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
