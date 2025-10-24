from __future__ import annotations

import datetime as dt
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator


class InstancePayload(BaseModel):
    id: str
    public_url: Optional[str] = None
    local_url: str
    session_name: Optional[str] = None
    host: Optional[str] = None
    started_at: dt.datetime

    @field_validator("started_at", mode="before")
    @classmethod
    def _parse_datetime(cls, value):
        if isinstance(value, dt.datetime):
            return value
        return dt.datetime.fromisoformat(value)


class InstanceResponse(BaseModel):
    status: str = "ok"
