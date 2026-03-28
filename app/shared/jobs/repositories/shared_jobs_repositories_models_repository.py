"""Application module for jobs repositories models repository workflows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.shared_database_base_model import Base

JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_SUCCEEDED = "succeeded"
JOB_STATUS_DEAD_LETTER = "dead_letter"

TERMINAL_JOB_STATUSES = {JOB_STATUS_SUCCEEDED, JOB_STATUS_DEAD_LETTER}


class Job(Base):
    """Durable background job row."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status_next_run_created", "status", "next_run_at", "created_at"),
        Index("ix_jobs_company_id", "company_id"),
        Index("ix_jobs_candidate_session_id", "candidate_session_id"),
        Index(
            "uq_jobs_company_job_type_idempotency_key",
            "company_id",
            "job_type",
            "idempotency_key",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=JOB_STATUS_QUEUED
    )
    attempt: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"), nullable=False, index=False
    )
    candidate_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidate_sessions.id"), nullable=True, index=False
    )
