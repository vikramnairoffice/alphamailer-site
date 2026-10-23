"""Additive fleet tables. Legacy instance and user tables are unchanged."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Worker(Base):
    __tablename__ = "fleet_workers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    platform: Mapped[str] = mapped_column(String(24))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    capabilities: Mapped[list] = mapped_column(JSON)
    accounts: Mapped[list] = mapped_column(JSON)
    max_parallel: Mapped[int] = mapped_column(Integer, default=1)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_seen: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))


class Job(Base):
    __tablename__ = "fleet_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    worker_id: Mapped[str] = mapped_column(String(64), index=True)
    operation: Mapped[str] = mapped_column(String(40))
    account_email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    execution: Mapped[str] = mapped_column(String(12), default="preview")
    payload: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(16), index=True, default="queued")
    slot_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lease_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))


class JobEvent(Base):
    __tablename__ = "fleet_job_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[str] = mapped_column(String(16))
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))


class Campaign(Base):
    __tablename__ = "fleet_campaigns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    manifest_hash: Mapped[str] = mapped_column(String(64))
    min_interval_seconds: Mapped[int] = mapped_column(Integer, default=0)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))


class CampaignAssignment(Base):
    __tablename__ = "fleet_campaign_assignments"
    __table_args__ = (UniqueConstraint("campaign_id", "lead_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("fleet_campaigns.id"), index=True)
    lead_id: Mapped[str] = mapped_column(String(120), index=True)
    worker_id: Mapped[str] = mapped_column(String(64))
    account_email: Mapped[str] = mapped_column(String(254))
    job_id: Mapped[str] = mapped_column(ForeignKey("fleet_jobs.id"), unique=True)
    input_hash: Mapped[str] = mapped_column(String(64))


class CampaignLeadIdentity(Base):
    """Durable ownership of a source lead across campaign submissions."""
    __tablename__ = "fleet_campaign_lead_identities"

    lead_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("fleet_campaigns.id"))


class CampaignAccountReservation(Base):
    """Serializes campaign submission for an account across workers."""
    __tablename__ = "fleet_campaign_account_reservations"

    account_email: Mapped[str] = mapped_column(String(254), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("fleet_campaigns.id"))


class CampaignPace(Base):
    __tablename__ = "fleet_campaign_pace"
    __table_args__ = (UniqueConstraint("campaign_id", "account_email"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("fleet_campaigns.id"))
    account_email: Mapped[str] = mapped_column(String(254))
    last_claim_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
