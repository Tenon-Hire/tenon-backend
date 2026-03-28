"""Application module for media repositories recordings media recordings core model workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base, TimestampMixin

RECORDING_ASSET_STATUS_UPLOADING = "uploading"
RECORDING_ASSET_STATUS_UPLOADED = "uploaded"
RECORDING_ASSET_STATUS_PROCESSING = "processing"
RECORDING_ASSET_STATUS_READY = "ready"
RECORDING_ASSET_STATUS_FAILED = "failed"
RECORDING_ASSET_STATUS_DELETED = "deleted"
RECORDING_ASSET_STATUS_PURGED = "purged"

RECORDING_ASSET_STATUSES = (
    RECORDING_ASSET_STATUS_UPLOADING,
    RECORDING_ASSET_STATUS_UPLOADED,
    RECORDING_ASSET_STATUS_PROCESSING,
    RECORDING_ASSET_STATUS_READY,
    RECORDING_ASSET_STATUS_FAILED,
    RECORDING_ASSET_STATUS_DELETED,
    RECORDING_ASSET_STATUS_PURGED,
)

RECORDING_ASSET_STATUS_CHECK_CONSTRAINT_NAME = "ck_recording_assets_status"
RECORDING_ASSET_STORAGE_KEY_UNIQUE_CONSTRAINT_NAME = "uq_recording_assets_storage_key"


def _status_check_expr() -> str:
    allowed = ",".join(f"'{status}'" for status in RECORDING_ASSET_STATUSES)
    return f"status IN ({allowed})"


class RecordingAsset(Base, TimestampMixin):
    """Video/blob asset metadata for candidate task handoff uploads."""

    __tablename__ = "recording_assets"
    __table_args__ = (
        UniqueConstraint(
            "storage_key",
            name=RECORDING_ASSET_STORAGE_KEY_UNIQUE_CONSTRAINT_NAME,
        ),
        CheckConstraint(
            _status_check_expr(),
            name=RECORDING_ASSET_STATUS_CHECK_CONSTRAINT_NAME,
        ),
        Index(
            "ix_recording_assets_candidate_session_task_created_at",
            "candidate_session_id",
            "task_id",
            "created_at",
        ),
        Index("ix_recording_assets_candidate_session_id", "candidate_session_id"),
        Index("ix_recording_assets_task_id", "task_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_session_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_sessions.id"),
        nullable=False,
    )
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RECORDING_ASSET_STATUS_UPLOADING,
        server_default=RECORDING_ASSET_STATUS_UPLOADING,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consent_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consent_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ai_notice_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    candidate_session = relationship("CandidateSession")
    task = relationship("Task")
    transcript = relationship("Transcript", back_populates="recording", uselist=False)


__all__ = [
    "RecordingAsset",
    "RECORDING_ASSET_STATUS_UPLOADING",
    "RECORDING_ASSET_STATUS_UPLOADED",
    "RECORDING_ASSET_STATUS_PROCESSING",
    "RECORDING_ASSET_STATUS_READY",
    "RECORDING_ASSET_STATUS_FAILED",
    "RECORDING_ASSET_STATUS_DELETED",
    "RECORDING_ASSET_STATUS_PURGED",
    "RECORDING_ASSET_STATUSES",
    "RECORDING_ASSET_STATUS_CHECK_CONSTRAINT_NAME",
    "RECORDING_ASSET_STORAGE_KEY_UNIQUE_CONSTRAINT_NAME",
]
