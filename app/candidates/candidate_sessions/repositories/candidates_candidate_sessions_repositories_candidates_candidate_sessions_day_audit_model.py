"""SQLAlchemy model for immutable day-cutoff audit records per candidate session."""

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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base


class CandidateDayAudit(Base):
    """Write-once cutoff evidence per candidate session/day."""

    __tablename__ = "candidate_day_audits"
    __table_args__ = (
        UniqueConstraint(
            "candidate_session_id",
            "day_index",
            name="uq_candidate_day_audits_session_day",
        ),
        CheckConstraint(
            "day_index IN (2, 3)", name="ck_candidate_day_audits_day_index"
        ),
        Index(
            "ix_candidate_day_audits_candidate_session_day",
            "candidate_session_id",
            "day_index",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_session_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_sessions.id", ondelete="CASCADE"), nullable=False
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cutoff_commit_sha: Mapped[str] = mapped_column(String(100), nullable=False)
    eval_basis_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    candidate_session = relationship("CandidateSession", back_populates="day_audits")
