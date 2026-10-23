"""Durable assignments. All worker mutations serialize on a database row lock.

The no-op UPDATE acquires a write lock on SQLite and a row lock on PostgreSQL.
Claims and reports share that lock; no process-local lock is relied upon.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import secrets
import uuid

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .fleet_models import Worker, Job, JobEvent, CampaignAssignment
from .fleet_schemas import ACTIVE_STATES, WorkerCreate, JobCreate, Heartbeat, Claim, Report

LEASE_SECONDS = 120


def now():
    return dt.datetime.now(dt.timezone.utc)


def aware(value):
    return value.replace(tzinfo=dt.timezone.utc) if value.tzinfo is None else value


def digest(value: str):
    return hashlib.sha256(value.encode()).hexdigest()


def reject(detail, code=409):
    raise HTTPException(code, detail)


def worker_view(worker):
    status = "never-connected" if worker.last_seen is None else (
        "online" if aware(worker.last_seen) > now() - dt.timedelta(seconds=LEASE_SECONDS) else "offline")
    view = {key: getattr(worker, key) for key in (
        "id", "name", "platform", "capabilities", "accounts", "max_parallel", "last_seen"
    )} | {"status": status, "protocol_version": 1}
    if view["last_seen"] is not None:
        view["last_seen"] = aware(view["last_seen"])
    return view


def job_view(job, include_payload=False):
    result = {key: getattr(job, key) for key in (
        "id", "worker_id", "operation", "account_email", "execution", "state", "slot_id",
        "session_id", "lease_expires_at", "result", "detail", "created_at", "updated_at"
    )}
    if include_payload:
        result["idempotency_key"] = job.idempotency_key
        result["message"] = job.payload.get("message")
        result["engine"] = job.payload.get("engine")
    for key, value in result.items():
        if isinstance(value, dt.datetime):
            result[key] = aware(value)
    return result | {"protocol_version": 1}


def event(db, job, state, detail="", result=None):
    job.state, job.detail, job.updated_at = state, detail, now()
    if result is not None:
        job.result = result
    db.add(JobEvent(job_id=job.id, state=state, detail=detail, created_at=job.updated_at))


def lock_worker(db: Session, worker_id: str):
    locked = db.execute(update(Worker).where(Worker.id == worker_id).values(name=Worker.name))
    if not locked.rowcount:
        reject("Worker not found", 404)
    return db.execute(select(Worker).where(Worker.id == worker_id)
                      .execution_options(populate_existing=True)).scalar_one()


def expire(db, worker_id):
    jobs = db.scalars(select(Job).where(Job.worker_id == worker_id,
        Job.state.in_(ACTIVE_STATES), Job.lease_expires_at <= now())).all()
    for job in jobs:
        event(db, job, "failed" if job.operation == "runtime.probe" else "uncertain",
              "Worker lease expired; execution was not retried.")
    db.flush()


def pair(db, body: WorkerCreate):
    token = secrets.token_urlsafe(32)
    worker = Worker(id=str(uuid.uuid4()), token_hash=digest(token), created_at=now(),
                    **body.model_dump())
    db.add(worker)
    db.commit()
    return worker_view(worker) | {"worker_token": token}


def submit(db, body: JobCreate, send_enabled=False):
    if body.engine and body.engine.command == "campaign.assignment":
        reject("Fleet assignments must be submitted through a campaign manifest", 422)
    if body.execution == "send" and not send_enabled:
        reject("Browser sending is disabled on this coordinator", 403)
    payload = body.model_dump(exclude={"confirmation"})
    request_hash = digest(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    existing = db.scalar(select(Job).where(Job.idempotency_key == body.idempotency_key))
    if existing:
        if existing.request_hash != request_hash:
            reject("Idempotency key already belongs to a different request")
        return job_view(existing)
    worker = lock_worker(db, body.worker_id)
    if body.engine and body.engine.command == "campaign.start":
        active_fleet = db.scalar(select(CampaignAssignment.id).join(
            Job, CampaignAssignment.job_id == Job.id).where(
            CampaignAssignment.worker_id == body.worker_id,
            CampaignAssignment.account_email == body.account_email,
            Job.state.in_(("queued", *ACTIVE_STATES))).limit(1))
        if active_fleet:
            reject("This account has fleet-owned leads; finish or cancel them before a standalone campaign")
    if body.operation not in worker.capabilities:
        reject("Worker does not support this operation", 422)
    if body.account_email and body.account_email not in worker.accounts:
        reject("Account is not assigned to this worker", 422)
    job = Job(id=str(uuid.uuid4()), idempotency_key=body.idempotency_key,
              request_hash=request_hash, worker_id=worker.id, operation=body.operation,
              account_email=body.account_email, execution=body.execution, payload=payload,
              state="queued", created_at=now(), updated_at=now())
    db.add(job)
    event(db, job, "queued")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Job).where(Job.idempotency_key == body.idempotency_key))
        if existing is None or existing.request_hash != request_hash:
            reject("Idempotency key conflict")
        return job_view(existing)
    return job_view(job)


def heartbeat(db, worker_id, body: Heartbeat):
    worker = lock_worker(db, worker_id)
    expire(db, worker_id)
    if worker.session_id and worker.session_id != body.session_id:
        if worker.last_seen and aware(worker.last_seen) > now() - dt.timedelta(seconds=LEASE_SECONDS):
            db.commit()  # retain any expired assignments
            reject("Another session is active; wait for it to become offline")
        # Old work can never transfer silently to a new runtime session.
        for job in db.scalars(select(Job).where(Job.worker_id == worker_id, Job.state.in_(ACTIVE_STATES))):
            event(db, job, "failed" if job.operation == "runtime.probe" else "uncertain", "Runtime session changed")
    renewed = []
    for ref in body.leases:
        job = db.get(Job, ref.job_id)
        if (job and job.worker_id == worker_id and job.session_id == body.session_id
                and job.state in ACTIVE_STATES and job.lease_hash == digest(ref.lease_token)
                and aware(job.lease_expires_at) > now()):
            job.lease_expires_at = now() + dt.timedelta(seconds=LEASE_SECONDS)
            renewed.append(job.id)
    worker.session_id, worker.last_seen = body.session_id, now()
    db.commit()
    return worker_view(worker) | {"renewed_job_ids": renewed, "lease_seconds": LEASE_SECONDS}


def check_session(worker, session_id):
    if worker.session_id != session_id:
        reject("Heartbeat with this runtime session before claiming or reporting")


def claim(db, worker_id, body: Claim):
    worker = lock_worker(db, worker_id)
    expire(db, worker_id)
    check_session(worker, body.session_id)
    if body.account_email and body.account_email not in worker.accounts:
        reject("Account is not assigned to this worker", 403)
    active = db.scalars(select(Job).where(Job.worker_id == worker_id, Job.state.in_(ACTIVE_STATES))).all()
    if len(active) >= worker.max_parallel or any(
        job.slot_id == body.slot_id or (body.account_email and job.account_email == body.account_email)
        for job in active
    ):
        db.commit()
        return {"job": None}
    job = db.scalar(select(Job).where(Job.worker_id == worker_id, Job.state == "queued",
        Job.account_email == body.account_email).order_by(Job.created_at, Job.id).limit(1))
    if not job:
        db.commit()
        return {"job": None}
    from .campaign_service import paced_claim
    if not paced_claim(db, job):
        db.commit()
        return {"job": None}
    token = secrets.token_urlsafe(32)
    job.session_id, job.slot_id = body.session_id, body.slot_id
    job.lease_hash, job.lease_expires_at = digest(token), now() + dt.timedelta(seconds=LEASE_SECONDS)
    event(db, job, "leased")
    db.commit()
    return {"job": job_view(job, include_payload=True), "lease_token": token}


def report(db, worker_id, body: Report, send_enabled=False):
    worker = lock_worker(db, worker_id)
    expire(db, worker_id)
    check_session(worker, body.session_id)
    job = db.get(Job, body.job_id)
    if not job or job.worker_id != worker_id:
        reject("Job not found", 404)
    if job.session_id != body.session_id or job.lease_hash != digest(body.lease_token):
        reject("Lease does not belong to this session", 403)
    if job.state == body.state and job.detail == body.detail and job.result == body.result:
        db.commit()
        return job_view(job)
    if job.state not in ACTIVE_STATES or aware(job.lease_expires_at) <= now():
        db.commit()
        reject("Lease expired or job is already terminal")
    transitions = {"leased": {"running", "failed", "uncertain"},
                   "running": {"sending", "succeeded", "failed", "uncertain"},
                   "sending": {"succeeded", "uncertain"}}
    if body.state not in transitions[job.state]:
        reject("Invalid job transition")
    if body.state == "sending" and job.execution != "send":
        reject("Preview jobs cannot send")
    if body.state == "sending" and not send_enabled:
        reject("Browser sending is disabled on this coordinator", 403)
    if body.state == "succeeded" and job.execution == "send" and job.state != "sending":
        reject("Sending must be acknowledged before completion")
    event(db, job, body.state, body.detail, body.result)
    db.commit()
    return job_view(job)


def jobs(db, worker_id=None, limit=100, offset=0):
    ids = [worker_id] if worker_id else db.scalars(select(Worker.id).order_by(Worker.id)).all()
    for identity in ids:
        lock_worker(db, identity)
        expire(db, identity)
        db.commit()
    query = select(Job).order_by(Job.created_at.desc(), Job.id.desc()).limit(limit).offset(offset)
    if worker_id:
        query = query.where(Job.worker_id == worker_id)
    return [job_view(job) for job in db.scalars(query)]


def rotate_token(db, worker_id, revoke=False):
    worker = lock_worker(db, worker_id)
    token = secrets.token_urlsafe(32)
    worker.token_hash = digest(token)
    worker.session_id = None
    worker.last_seen = None
    for job in db.scalars(select(Job).where(Job.worker_id == worker_id,
                                           Job.state.in_((*ACTIVE_STATES, "queued")))):
        state = "cancelled" if job.state == "queued" else "uncertain"
        event(db, job, state, "Worker credential revoked; execution must be reconciled")
    db.commit()
    return {"worker_id": worker_id, "revoked": revoke, **({} if revoke else {"worker_token": token})}


def cancel(db, job_id):
    job = db.get(Job, job_id)
    if not job:
        reject("Job not found", 404)
    lock_worker(db, job.worker_id)
    db.refresh(job)
    if job.state != "queued":
        reject("Only queued jobs can be cancelled safely")
    event(db, job, "cancelled", "Cancelled by operator")
    db.commit()
    return job_view(job)
