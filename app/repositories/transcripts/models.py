from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin

TRANSCRIPT_STATUS_PENDING = "pending"
TRANSCRIPT_STATUS_PROCESSING = "processing"
TRANSCRIPT_STATUS_READY = "ready"
TRANSCRIPT_STATUS_FAILED = "failed"

TRANSCRIPT_STATUSES = (
    TRANSCRIPT_STATUS_PENDING,
    TRANSCRIPT_STATUS_PROCESSING,
    TRANSCRIPT_STATUS_READY,
    TRANSCRIPT_STATUS_FAILED,
)

TRANSCRIPT_STATUS_CHECK_CONSTRAINT_NAME = "ck_transcripts_status"
TRANSCRIPT_RECORDING_UNIQUE_CONSTRAINT_NAME = "uq_transcripts_recording_id"


def _status_check_expr() -> str:
    allowed = ",".join(f"'{status}'" for status in TRANSCRIPT_STATUSES)
    return f"status IN ({allowed})"


class Transcript(Base, TimestampMixin):
    """Transcript rows associated with a recording asset."""

    __tablename__ = "transcripts"
    __table_args__ = (
        UniqueConstraint(
            "recording_id",
            name=TRANSCRIPT_RECORDING_UNIQUE_CONSTRAINT_NAME,
        ),
        CheckConstraint(
            _status_check_expr(),
            name=TRANSCRIPT_STATUS_CHECK_CONSTRAINT_NAME,
        ),
        Index("ix_transcripts_recording_id", "recording_id"),
        Index("ix_transcripts_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recording_id: Mapped[int] = mapped_column(
        ForeignKey("recording_assets.id"),
        nullable=False,
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    segments_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TRANSCRIPT_STATUS_PENDING,
        server_default=TRANSCRIPT_STATUS_PENDING,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    recording = relationship("RecordingAsset", back_populates="transcript")


__all__ = [
    "Transcript",
    "TRANSCRIPT_STATUSES",
    "TRANSCRIPT_STATUS_PENDING",
    "TRANSCRIPT_STATUS_PROCESSING",
    "TRANSCRIPT_STATUS_READY",
    "TRANSCRIPT_STATUS_FAILED",
    "TRANSCRIPT_STATUS_CHECK_CONSTRAINT_NAME",
    "TRANSCRIPT_RECORDING_UNIQUE_CONSTRAINT_NAME",
]
