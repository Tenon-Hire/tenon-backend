from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    column,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base


class CandidateSession(Base):
    """Candidate session record for invited candidates."""

    __tablename__ = "candidate_sessions"
    __table_args__ = (
        UniqueConstraint(
            "simulation_id",
            "invite_email",
            name="uq_candidate_session_simulation_invite_email",
        ),
        Index(
            "uq_candidate_sessions_simulation_invite_email_ci",
            "simulation_id",
            func.lower(column("invite_email")),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    simulation_id: Mapped[int] = mapped_column(
        ForeignKey("simulations.id"), nullable=False
    )
    scenario_version_id: Mapped[int] = mapped_column(
        ForeignKey("scenario_versions.id"), nullable=False
    )
    candidate_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_email: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_auth0_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_auth0_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    token: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invite_email_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    invite_email_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    invite_email_last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    invite_email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scheduled_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    candidate_timezone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    github_username: Mapped[str | None] = mapped_column(String(39), nullable=True)
    day_windows_json: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    schedule_locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consent_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consent_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ai_notice_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    simulation = relationship("Simulation", back_populates="candidate_sessions")
    scenario_version = relationship(
        "ScenarioVersion", back_populates="candidate_sessions"
    )
    candidate_user = relationship("User", back_populates="candidate_sessions")
    submissions = relationship(
        "Submission", back_populates="candidate_session", cascade="all, delete-orphan"
    )
    fit_profile = relationship(
        "FitProfile",
        back_populates="candidate_session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    evaluation_runs = relationship(
        "EvaluationRun",
        back_populates="candidate_session",
        cascade="all, delete-orphan",
    )
    workspaces = relationship(
        "Workspace", back_populates="candidate_session", cascade="all, delete-orphan"
    )
    workspace_groups = relationship(
        "WorkspaceGroup",
        back_populates="candidate_session",
        cascade="all, delete-orphan",
    )
    day_audits = relationship(
        "CandidateDayAudit",
        back_populates="candidate_session",
        cascade="all, delete-orphan",
    )


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
        ForeignKey("candidate_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cutoff_commit_sha: Mapped[str] = mapped_column(String(100), nullable=False)
    eval_basis_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    candidate_session = relationship("CandidateSession", back_populates="day_audits")
