from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth, models
from .config import get_settings
from .database import get_db


router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@router.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(request: Request, response: Response, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    stmt = select(models.User).where(models.User.email == email.lower())
    user = db.execute(stmt).scalar_one_or_none()
    if not user or not auth.verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"}, status_code=status.HTTP_401_UNAUTHORIZED)
    token = auth.create_session_token(user.id)
    settings = get_settings()
    resp = RedirectResponse(url="/admin/", status_code=status.HTTP_302_FOUND)
    resp.set_cookie(settings.session_cookie_name, token, httponly=True, max_age=60 * 60 * 8)
    return resp


@router.get("/logout")
async def logout(response: Response):
    settings = get_settings()
    resp = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(settings.session_cookie_name)
    return resp


def _ensure_aware(dt_value: dt.datetime) -> dt.datetime:
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=dt.timezone.utc)
    return dt_value.astimezone(dt.timezone.utc)


def _fmt_dt(dt_val: dt.datetime) -> str:
    try:
        return _ensure_aware(dt_val).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(dt_val)


def _ago_text(ref: dt.datetime, now: dt.datetime) -> str:
    delta = int((_ensure_aware(now) - _ensure_aware(ref)).total_seconds())
    if delta < 60:
        return f"{delta}s ago"
    if delta < 3600:
        return f"{delta//60}m ago"
    if delta < 86400:
        return f"{delta//3600}h ago"
    return f"{delta//86400}d ago"


def _serialize_instance(instance: models.Instance, active_cutoff: dt.datetime) -> Dict[str, Any]:
    last_seen = _ensure_aware(instance.last_seen)
    started_at = _ensure_aware(instance.started_at)
    cutoff = _ensure_aware(active_cutoff)
    status = "active" if last_seen >= cutoff else "offline"
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "id": instance.id,
        "public_url": instance.public_url,
        "local_url": instance.local_url,
        "session_name": instance.session_name,
        "host": instance.host,
        "started_at": started_at,
        "last_seen": last_seen,
        "started_fmt": _fmt_dt(started_at),
        "last_seen_fmt": _fmt_dt(last_seen),
        "last_seen_ago": _ago_text(last_seen, now),
        "status": status,
    }


@router.get("/")
async def dashboard(request: Request, user: models.User = Depends(auth.require_login), db: Session = Depends(get_db)):
    settings = get_settings()
    stmt = select(models.Instance).order_by(models.Instance.last_seen.desc())
    rows = db.execute(stmt).scalars().all()
    now = dt.datetime.now(dt.timezone.utc)
    active_cutoff = now - dt.timedelta(minutes=settings.active_minutes)
    # Only show currently active instances
    active_rows = [r for r in rows if _ensure_aware(r.last_seen) >= active_cutoff]
    instances = [_serialize_instance(row, active_cutoff) for row in active_rows]
    active_count = len(instances)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "instances": instances,
            "active_count": active_count,
            "total_count": active_count,
        },
    )


@router.get("/users")
async def users_page(request: Request, user: models.User = Depends(auth.require_admin), db: Session = Depends(get_db), message: str | None = None):
    stmt = select(models.User).order_by(models.User.created_at.desc())
    users = db.execute(stmt).scalars().all()
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "message": message,
        },
    )


@router.post("/users")
async def create_user(
    request: Request,
    user: models.User = Depends(auth.require_admin),
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    is_admin: bool = Form(False),
):
    email_clean = email.strip().lower()
    if not email_clean or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and password required")
    existing = db.execute(select(models.User).where(models.User.email == email_clean)).scalar_one_or_none()
    if existing:
        return templates.TemplateResponse(
            "users.html",
            {
                "request": request,
                "user": user,
                "users": db.execute(select(models.User).order_by(models.User.created_at.desc())).scalars().all(),
                "message": "User already exists",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    is_admin_flag = False
    if isinstance(is_admin, str):
        is_admin_flag = is_admin.lower() in {"1", "true", "on", "yes"}
    else:
        is_admin_flag = bool(is_admin)

    new_user = models.User(
        email=email_clean,
        hashed_password=auth.hash_password(password),
        is_admin=is_admin_flag,
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/admin/users?message=User%20created", status_code=status.HTTP_302_FOUND)
