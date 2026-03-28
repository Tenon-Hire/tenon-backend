"""Application module for submissions repositories submissions fit profile model workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base


class FitProfile(Base):
    """Model for storing fit profiles for candidate sessions."""

    __tablename__ = "fit_profiles"
    __table_args__ = (
        UniqueConstraint(
            "candidate_session_id",
            name="uq_fit_profiles_candidate_session_id",
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

    candidate_session = relationship("CandidateSession", back_populates="fit_profile")
