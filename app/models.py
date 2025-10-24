from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Instance(Base):
    __tablename__ = "instances"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    public_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    local_url: Mapped[str] = mapped_column(String(512), nullable=False)
    session_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
