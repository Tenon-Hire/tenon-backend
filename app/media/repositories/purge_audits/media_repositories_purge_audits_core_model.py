"""Media purge audit records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.shared_database_base_model import Base

MEDIA_PURGE_ACTOR_SYSTEM = "system"
MEDIA_PURGE_ACTOR_OPERATOR = "operator"
MEDIA_PURGE_REASON_RETENTION_EXPIRED = "retention_expired"
MEDIA_PURGE_REASON_DATA_REQUEST = "data_request"
MEDIA_PURGE_OUTCOME_SUCCESS = "success"
MEDIA_PURGE_OUTCOME_PARTIAL = "partial"
MEDIA_PURGE_OUTCOME_FAILED = "failed"
MEDIA_PURGE_OUTCOME_SKIPPED = "skipped"


class MediaPurgeAudit(Base):
    """Privacy-safe audit record for media purge attempts."""

    __tablename__ = "media_purge_audits"
    __table_args__ = (
        Index("ix_media_purge_audits_media_created_at", "media_id", "created_at"),
        Index("ix_media_purge_audits_reason_created_at", "purge_reason", "created_at"),
        Index(
            "ix_media_purge_audits_candidate_session_created_at",
            "candidate_session_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_id: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trial_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purge_reason: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = [
    "MEDIA_PURGE_ACTOR_OPERATOR",
    "MEDIA_PURGE_ACTOR_SYSTEM",
    "MEDIA_PURGE_OUTCOME_FAILED",
    "MEDIA_PURGE_OUTCOME_PARTIAL",
    "MEDIA_PURGE_OUTCOME_SKIPPED",
    "MEDIA_PURGE_OUTCOME_SUCCESS",
    "MEDIA_PURGE_REASON_DATA_REQUEST",
    "MEDIA_PURGE_REASON_RETENTION_EXPIRED",
    "MediaPurgeAudit",
]
