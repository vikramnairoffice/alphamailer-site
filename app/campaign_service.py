"""Immutable fleet manifests and aggregate state over the existing job journal."""
from __future__ import annotations

import datetime as dt
import json
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import fleet_service as fleet
from .fleet_models import (Campaign, CampaignAccountReservation, CampaignAssignment,
                           CampaignLeadIdentity, CampaignPace, Job)
from .fleet_schemas import CampaignCreate, EngineCommand, JobCreate


def _hash(value):
    return fleet.digest(json.dumps(value, sort_keys=True, separators=(",", ":")))


def view(db: Session, campaign_id: str, *, include_assignments=False):
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        fleet.reject("Campaign not found", 404)
    rows = db.execute(select(CampaignAssignment, Job).join(
        Job, CampaignAssignment.job_id == Job.id).where(
        CampaignAssignment.campaign_id == campaign_id).order_by(CampaignAssignment.lead_id)).all()
    counts = {state: 0 for state in ("queued", "leased", "running", "sending", "succeeded", "failed", "uncertain", "cancelled")}
    assignments = []
    for assignment, job in rows:
        counts[job.state] += 1
        assignments.append({"id": assignment.id, "lead_id": assignment.lead_id,
                            "worker_id": assignment.worker_id, "account_email": assignment.account_email,
                            "job_id": job.id, "state": job.state, "detail": job.detail,
                            "result": job.result})
    active = sum(counts[state] for state in ("queued", "leased", "running", "sending"))
    state = ("cancelling" if campaign.cancel_requested and active else
             "running" if active else
             "uncertain" if counts["uncertain"] else
             "failed" if counts["failed"] else
             "cancelled" if counts["cancelled"] else "succeeded")
    result = {"id": campaign.id, "state": state, "cancel_requested": campaign.cancel_requested,
              "total": len(rows), "counts": counts, "created_at": campaign.created_at}
    if include_assignments:
        result["assignments"] = assignments
    return result


def submit(db: Session, body: CampaignCreate, send_enabled=False):
    manifest = body.model_dump(exclude={"confirmation"})
    manifest_hash = _hash(manifest)
    existing = db.scalar(select(Campaign).where(Campaign.idempotency_key == body.idempotency_key))
    if existing:
        if existing.manifest_hash != manifest_hash:
            fleet.reject("Campaign key belongs to a different manifest")
        return view(db, existing.id, include_assignments=True)
    if any(item.execution == "send" for item in body.assignments) and not send_enabled:
        fleet.reject("Worker delivery is disabled on this coordinator", 403)
    # Read the assignment journal as well as relying on the new identity key:
    # a database created before the identity table can contain older campaigns.
    used_lead = db.scalar(select(CampaignAssignment.lead_id).where(
        CampaignAssignment.lead_id.in_([item.lead_id for item in body.assignments])).limit(1))
    if used_lead is not None:
        fleet.reject("Lead ID already belongs to another campaign; use a new ID for an intentional rerun")

    workers = {}
    for identity in sorted({item.worker_id for item in body.assignments}):
        workers[identity] = fleet.lock_worker(db, identity)
    account_owner = {}
    for item in body.assignments:
        worker = workers[item.worker_id]
        if item.operation not in worker.capabilities or item.account_email not in worker.accounts:
            fleet.reject("Assignment worker lacks the operation or account", 422)
        previous = account_owner.setdefault(item.account_email, item.worker_id)
        if previous != item.worker_id:
            fleet.reject("One campaign account must belong to one worker", 422)
        standalone_jobs = db.scalars(select(Job).where(
            Job.worker_id == item.worker_id, Job.account_email == item.account_email,
            Job.operation == "engine.command", Job.state.in_(("queued", *fleet.ACTIVE_STATES)))).all()
        if any((job.payload.get("engine") or {}).get("command") == "campaign.start"
               for job in standalone_jobs):
            fleet.reject("This account has an active standalone campaign job")

    reservations = {account: db.scalar(select(CampaignAccountReservation).where(
        CampaignAccountReservation.account_email == account).with_for_update())
        for account in sorted(account_owner)}
    active_fleet = db.scalar(select(Job.id).join(
        CampaignAssignment, CampaignAssignment.job_id == Job.id).where(
        CampaignAssignment.account_email.in_(account_owner),
        Job.state.in_(("queued", *fleet.ACTIVE_STATES))).limit(1))
    if active_fleet is not None:
        fleet.reject("Account already has an active fleet campaign; finish or cancel it first")

    campaign = Campaign(id=str(uuid.uuid4()), idempotency_key=body.idempotency_key,
                        manifest_hash=manifest_hash, min_interval_seconds=body.min_interval_seconds,
                        cancel_requested=False, created_at=fleet.now())
    db.add(campaign)
    for account in account_owner:
        reservation = reservations[account]
        if reservation is None:
            db.add(CampaignAccountReservation(account_email=account,
                                              campaign_id=campaign.id))
        else:
            reservation.campaign_id = campaign.id
        db.add(CampaignPace(id=str(uuid.uuid4()), campaign_id=campaign.id,
                            account_email=account))
    for item in body.assignments:
        assignment_id = str(uuid.uuid5(uuid.UUID(campaign.id), item.lead_id))
        db.add(CampaignLeadIdentity(lead_id=item.lead_id, campaign_id=campaign.id))
        if item.operation == "engine.command":
            engine = EngineCommand(command="campaign.assignment", parameters={
                "campaign_id": campaign.id, "assignment_id": assignment_id,
                "lead_id": item.lead_id, "lead": item.lead, "config": item.config,
                "delivery": item.delivery})
            message = None
        else:
            engine = None
            message = item.message
        job_body = JobCreate(idempotency_key="fleet:" + assignment_id,
            worker_id=item.worker_id, account_email=item.account_email,
            operation=item.operation, execution=item.execution,
            confirmation="SEND" if item.execution == "send" else None,
            message=message, engine=engine)
        payload = job_body.model_dump(exclude={"confirmation"})
        job = Job(id=str(uuid.uuid4()), idempotency_key=job_body.idempotency_key,
                  request_hash=_hash(payload), worker_id=item.worker_id,
                  operation=item.operation, account_email=item.account_email,
                  execution=item.execution, payload=payload, state="queued",
                  created_at=fleet.now(), updated_at=fleet.now())
        db.add(job)
        db.add(CampaignAssignment(id=assignment_id, campaign_id=campaign.id,
            lead_id=item.lead_id, worker_id=item.worker_id,
            account_email=item.account_email, job_id=job.id,
            input_hash=_hash(item.model_dump())))
        fleet.event(db, job, "queued", "Fleet assignment queued")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Campaign).where(Campaign.idempotency_key == body.idempotency_key))
        if existing is not None and existing.manifest_hash == manifest_hash:
            return view(db, existing.id, include_assignments=True)
        fleet.reject("Campaign key or lead identity conflict")
    return view(db, campaign.id, include_assignments=True)


def paced_claim(db: Session, job: Job):
    assignment = db.scalar(select(CampaignAssignment).where(CampaignAssignment.job_id == job.id))
    if assignment is None:
        return True
    campaign = db.get(Campaign, assignment.campaign_id)
    if campaign.cancel_requested:
        return False
    paces = db.execute(select(CampaignPace, Campaign).join(
        Campaign, CampaignPace.campaign_id == Campaign.id).where(
        CampaignPace.account_email == assignment.account_email).with_for_update()).all()
    pace = next(row for row, owner in paces if row.campaign_id == campaign.id)
    current = fleet.now()
    for row, owner in paces:
        if row.last_claim_at and fleet.aware(row.last_claim_at) + dt.timedelta(
                seconds=max(owner.min_interval_seconds, campaign.min_interval_seconds)) > current:
            return False
    pace.last_claim_at = current
    return True


def cancel(db: Session, campaign_id: str):
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        fleet.reject("Campaign not found", 404)
    rows = db.execute(select(CampaignAssignment, Job).join(
        Job, CampaignAssignment.job_id == Job.id).where(
        CampaignAssignment.campaign_id == campaign_id)).all()
    for identity in sorted({assignment.worker_id for assignment, _ in rows}):
        fleet.lock_worker(db, identity)
    campaign.cancel_requested = True
    for _, job in rows:
        db.refresh(job)
        if job.state == "queued":
            fleet.event(db, job, "cancelled", "Campaign cancelled before claim")
    db.commit()
    return view(db, campaign_id, include_assignments=True)
