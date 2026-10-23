"""Version 1 boundary shared by the independent Android and browser clients."""
from __future__ import annotations

import base64
import binascii
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PROTOCOL_VERSION = 1
MAX_WORKER_PARALLEL = 10
Operation = Literal["runtime.probe", "gmail.compose", "gmail.draft", "engine.command"]
ACTIVE_STATES = ("leased", "running", "sending")
EMAIL = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not EMAIL.fullmatch(value) or len(value) > 254:
        raise ValueError("A plain email address is required")
    return value


class WorkerCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    platform: Literal["android", "chrome", "firefox", "test"]
    capabilities: list[Operation] = Field(min_length=1, max_length=4)
    accounts: list[str] = Field(default_factory=list, max_length=MAX_WORKER_PARALLEL)
    max_parallel: int = Field(default=1, ge=1, le=MAX_WORKER_PARALLEL)

    @field_validator("accounts")
    @classmethod
    def validate_accounts(cls, values):
        return sorted(set(normalize_email(value) for value in values))


class GoogleOAuthStart(StrictModel):
    protocol_version: Literal[1] = 1
    email: str = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        return normalize_email(value)


class GoogleOAuthSession(StrictModel):
    protocol_version: Literal[1] = 1
    session_id: str = Field(min_length=36, max_length=36)
    handoff_key: str = Field(min_length=40, max_length=128)


class GoogleOAuthRefresh(StrictModel):
    protocol_version: Literal[1] = 1
    refresh_token: str = Field(min_length=1, max_length=8192)
    receipt: str = Field(min_length=40, max_length=16384)


class Attachment(StrictModel):
    name: str = Field(min_length=1, max_length=180)
    mime_type: str = Field(default="application/octet-stream", min_length=1, max_length=120)
    data_base64: str = Field(max_length=2_800_000)

    @field_validator("name")
    @classmethod
    def filename_only(cls, value):
        if any(char in value for char in ("/", "\\", "\x00", "\r", "\n")) or value in (".", ".."):
            raise ValueError("Attachment name must be a filename")
        return value

    @field_validator("data_base64")
    @classmethod
    def valid_base64(cls, value):
        try:
            data = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Invalid base64 attachment") from exc
        if len(data) > 2_000_000:
            raise ValueError("Initial worker supports at most 2 MB per attachment")
        return value


class PreparedMessage(StrictModel):
    to: list[str] = Field(min_length=1, max_length=50)
    subject: str = Field(max_length=998)
    body: str = Field(max_length=250_000)
    body_format: Literal["text", "html"] = "text"
    attachments: list[Attachment] = Field(default_factory=list, max_length=4)
    # Used only for draft lookup, never interpreted as a Gmail UI URL.
    rfc822_message_id: str | None = Field(default=None, max_length=254)

    @field_validator("to")
    @classmethod
    def recipients(cls, values):
        return [normalize_email(value) for value in values]

    @field_validator("subject")
    @classmethod
    def single_line_subject(cls, value):
        if "\r" in value or "\n" in value:
            raise ValueError("Subject must be a single line")
        return value

    @field_validator("rfc822_message_id")
    @classmethod
    def message_id(cls, value):
        atom = r"[A-Za-z0-9._+\-]+@[A-Za-z0-9.\-]+"
        if value is not None and not re.fullmatch(rf"(?:{atom}|<{atom}>)", value):
            raise ValueError("A single RFC 822 Message-ID is required")
        return value


class EngineCommand(StrictModel):
    command: Literal["message.prepare", "message.execute", "campaign.start", "campaign.status",
                     "campaign.pause", "campaign.resume", "campaign.stop", "campaign.assignment"]
    parameters: dict = Field(default_factory=dict)

    @field_validator("parameters")
    @classmethod
    def bounded(cls, value):
        import json
        if len(json.dumps(value)) > 250_000:
            raise ValueError("Engine parameters exceed the command limit")
        return value


class JobCreate(StrictModel):
    protocol_version: Literal[1] = 1
    idempotency_key: str = Field(min_length=8, max_length=120)
    worker_id: str = Field(min_length=1, max_length=64)
    operation: Operation
    account_email: str | None = None
    execution: Literal["preview", "send"] = "preview"
    confirmation: str | None = None
    message: PreparedMessage | None = None
    engine: EngineCommand | None = None

    @field_validator("account_email")
    @classmethod
    def account(cls, value):
        return normalize_email(value) if value is not None else None

    @model_validator(mode="after")
    def validate_operation(self):
        if self.operation == "runtime.probe":
            if self.engine is not None or self.message is not None or self.account_email is not None or self.execution != "preview":
                raise ValueError("Runtime probes do not accept message/account/send fields")
        elif self.operation == "engine.command":
            if self.engine is None or self.message is not None or self.account_email is None:
                raise ValueError("Engine commands require an assigned account and engine parameters")
            if self.engine.command == "message.execute" and self.execution != "send":
                raise ValueError("Remote delivery or draft creation requires explicit execution intent")
            if self.engine.command not in ("message.execute", "campaign.start", "campaign.assignment") and self.execution != "preview":
                raise ValueError("Preparation and campaign controls do not send mail")
        else:
            if self.engine is not None or self.message is None or self.account_email is None:
                raise ValueError("Gmail jobs require an account and prepared message")
            if self.operation == "gmail.draft" and not self.message.rfc822_message_id:
                raise ValueError("Draft jobs require the exact draft RFC 822 Message-ID")
        if self.execution == "send" and self.confirmation != "SEND":
            raise ValueError("Sending requires explicit SEND confirmation")
        return self


class CampaignItem(StrictModel):
    lead_id: str = Field(min_length=1, max_length=120)
    worker_id: str = Field(min_length=1, max_length=64)
    account_email: str
    operation: Literal["engine.command", "gmail.compose", "gmail.draft"]
    execution: Literal["preview", "send"] = "preview"
    delivery: Literal["send", "draft"] = "send"
    message: PreparedMessage | None = None
    lead: str | dict | None = None
    config: dict | None = None

    @field_validator("account_email")
    @classmethod
    def account(cls, value):
        return normalize_email(value)

    @model_validator(mode="after")
    def validate_item(self):
        if self.operation == "engine.command":
            if self.message is not None or self.lead is None or self.config is None:
                raise ValueError("Engine assignments require a lead and configuration")
        elif self.message is None or self.lead is not None or self.config is not None:
            raise ValueError("Browser assignments require one frozen prepared message")
        if self.operation == "gmail.draft" and not self.message.rfc822_message_id:
            raise ValueError("Draft assignments need an exact RFC 822 Message-ID")
        return self


class CampaignCreate(StrictModel):
    protocol_version: Literal[1] = 1
    idempotency_key: str = Field(min_length=8, max_length=120)
    min_interval_seconds: int = Field(default=0, ge=0, le=3600)
    assignments: list[CampaignItem] = Field(min_length=1, max_length=500)
    confirmation: str | None = None

    @model_validator(mode="after")
    def validate_manifest(self):
        ids = [item.lead_id for item in self.assignments]
        if len(ids) != len(set(ids)):
            raise ValueError("Each lead_id must appear once in a campaign")
        if any(item.execution == "send" for item in self.assignments) and self.confirmation != "SEND":
            raise ValueError("Sending requires explicit SEND confirmation")
        import json
        if len(json.dumps(self.model_dump())) > 2_000_000:
            raise ValueError("Campaign manifest exceeds 2 MB")
        return self


class LeaseRef(StrictModel):
    job_id: str = Field(min_length=1, max_length=64)
    lease_token: str = Field(min_length=20, max_length=128)


class Heartbeat(StrictModel):
    protocol_version: Literal[1] = 1
    session_id: str = Field(min_length=8, max_length=64)
    leases: list[LeaseRef] = Field(default_factory=list, max_length=MAX_WORKER_PARALLEL)


class Claim(StrictModel):
    protocol_version: Literal[1] = 1
    session_id: str = Field(min_length=8, max_length=64)
    slot_id: str = Field(min_length=1, max_length=80)
    account_email: str | None = None

    @field_validator("account_email")
    @classmethod
    def account(cls, value):
        return normalize_email(value) if value is not None else None


class Report(LeaseRef):
    protocol_version: Literal[1] = 1
    session_id: str = Field(min_length=8, max_length=64)
    state: Literal["running", "sending", "succeeded", "failed", "uncertain"]
    detail: str = Field(default="", max_length=1000)
    result: dict = Field(default_factory=dict)

    @field_validator("result")
    @classmethod
    def bounded_result(cls, value):
        import json
        if len(json.dumps(value)) > 32_000:
            raise ValueError("Result is too large")
        return value
