"""Application module for submissions repositories submissions winoe report model workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base


class WinoeReport(Base):
    """Model for storing winoe reports for candidate sessions."""

    __tablename__ = "winoe_reports"
    __table_args__ = (
        UniqueConstraint(
            "candidate_session_id",
            name="uq_winoe_reports_candidate_session_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    candidate_session_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    candidate_session = relationship("CandidateSession", back_populates="winoe_report")
