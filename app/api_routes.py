from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth, models
from .config import get_settings
from .database import get_db
from .schemas import InstancePayload, InstanceResponse


router = APIRouter(prefix="/api", tags=["api"])


def _ensure_aware(dt_value: dt.datetime) -> dt.datetime:
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=dt.timezone.utc)
    return dt_value.astimezone(dt.timezone.utc)


def _serialize_instance(inst: models.Instance, active_cutoff: dt.datetime) -> dict:
    last_seen = _ensure_aware(inst.last_seen)
    started = _ensure_aware(inst.started_at)
    status = "active" if last_seen >= active_cutoff else "offline"
    return {
        "id": inst.id,
        "public_url": inst.public_url,
        "local_url": inst.local_url,
        "session_name": inst.session_name,
        "host": inst.host,
        "started_at": started,
        "last_seen": last_seen,
        "status": status,
    }


@router.post("/instances", response_model=InstanceResponse)
async def upsert_instance(payload: InstancePayload, _: None = Depends(auth.require_api_token), db: Session = Depends(get_db)):
    now = dt.datetime.now(dt.timezone.utc)
    started_at = _ensure_aware(payload.started_at)
    instance = db.get(models.Instance, payload.id)
    if instance:
        instance.public_url = payload.public_url
        instance.local_url = payload.local_url
        instance.session_name = payload.session_name
        instance.host = payload.host
        instance.started_at = started_at
        instance.last_seen = now
    else:
        instance = models.Instance(
            id=payload.id,
            public_url=payload.public_url,
            local_url=payload.local_url,
            session_name=payload.session_name,
            host=payload.host,
            started_at=started_at,
            last_seen=now,
        )
        db.add(instance)
    db.commit()
    return InstanceResponse()


@router.get("/instances")
async def list_instances(status: str | None = None, _: None = Depends(auth.require_api_token), db: Session = Depends(get_db)):
    settings = get_settings()
    stmt = select(models.Instance).order_by(models.Instance.last_seen.desc())
    instances = db.execute(stmt).scalars().all()
    active_cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=settings.active_minutes)
    result = []
    for inst in instances:
        serialized = _serialize_instance(inst, active_cutoff)
        if status and serialized["status"] != status:
            continue
        result.append(serialized)
    return {"items": result}
