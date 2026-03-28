"""Application module for submissions repositories task drafts submissions task drafts core model workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base


class TaskDraft(Base):
    """Draft content for a candidate's task, finalized at day close."""

    __tablename__ = "task_drafts"
    __table_args__ = (
        UniqueConstraint(
            "candidate_session_id",
            "task_id",
            name="uq_task_drafts_candidate_session_task",
        ),
        Index("ix_task_drafts_candidate_session_id", "candidate_session_id"),
        Index("ix_task_drafts_task_id", "task_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_session_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_sessions.id"), nullable=False
    )
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finalized_submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("submissions.id"), nullable=True
    )

    candidate_session = relationship("CandidateSession")
    task = relationship("Task")
    finalized_submission = relationship("Submission")
