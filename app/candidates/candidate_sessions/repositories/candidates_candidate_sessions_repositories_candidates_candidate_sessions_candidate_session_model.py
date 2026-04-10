"""Application module for candidates candidate sessions repositories candidates candidate sessions candidate session model workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
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

from app.shared.database.shared_database_base_model import Base


class CandidateSession(Base):
    """Candidate session record for invited candidates."""

    __tablename__ = "candidate_sessions"
    __table_args__ = (
        UniqueConstraint(
            "trial_id",
            "invite_email",
            name="uq_candidate_session_trial_invite_email",
        ),
        Index(
            "uq_candidate_sessions_trial_invite_email_ci",
            "trial_id",
            func.lower(column("invite_email")),
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("trials.id"), nullable=False)
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

    trial = relationship("Trial", back_populates="candidate_sessions")
    scenario_version = relationship(
        "ScenarioVersion", back_populates="candidate_sessions"
    )
    candidate_user = relationship("User", back_populates="candidate_sessions")
    submissions = relationship(
        "Submission", back_populates="candidate_session", cascade="all, delete-orphan"
    )
    winoe_report = relationship(
        "WinoeReport",
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
