"""Application module for evaluations repositories evaluations run model workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base

from .evaluations_repositories_evaluations_constants_model import (
    EVALUATION_RUN_COMPLETED_AT_CHECK_CONSTRAINT_NAME,
    EVALUATION_RUN_RECOMMENDATION_CHECK_CONSTRAINT_NAME,
    EVALUATION_RUN_STATUS_CHECK_CONSTRAINT_NAME,
    EVALUATION_RUN_STATUS_PENDING,
    recommendation_check_expr,
    status_check_expr,
)


class EvaluationRun(Base):
    """Header row for one immutable evaluation attempt."""

    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            status_check_expr(), name=EVALUATION_RUN_STATUS_CHECK_CONSTRAINT_NAME
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name=EVALUATION_RUN_COMPLETED_AT_CHECK_CONSTRAINT_NAME,
        ),
        CheckConstraint(
            recommendation_check_expr(),
            name=EVALUATION_RUN_RECOMMENDATION_CHECK_CONSTRAINT_NAME,
        ),
        Index(
            "ix_evaluation_runs_candidate_session_scenario_version",
            "candidate_session_id",
            "scenario_version_id",
        ),
        Index(
            "ix_evaluation_runs_candidate_session_started_at",
            "candidate_session_id",
            "started_at",
        ),
        Index(
            "ix_evaluation_runs_candidate_session_status_started_at",
            "candidate_session_id",
            "status",
            "started_at",
        ),
        Index("ix_evaluation_runs_job_id", "job_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_session_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_sessions.id", ondelete="CASCADE"), nullable=False
    )
    scenario_version_id: Mapped[int] = mapped_column(
        ForeignKey("scenario_versions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=EVALUATION_RUN_STATUS_PENDING,
        server_default=EVALUATION_RUN_STATUS_PENDING,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(255), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(255), nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    basis_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    overall_fit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_report_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    day2_checkpoint_sha: Mapped[str] = mapped_column(String(100), nullable=False)
    day3_final_sha: Mapped[str] = mapped_column(String(100), nullable=False)
    cutoff_commit_sha: Mapped[str] = mapped_column(String(100), nullable=False)
    transcript_reference: Mapped[str] = mapped_column(String(255), nullable=False)

    candidate_session = relationship(
        "CandidateSession", back_populates="evaluation_runs"
    )
    scenario_version = relationship("ScenarioVersion")
    day_scores = relationship(
        "EvaluationDayScore",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="EvaluationDayScore.day_index",
    )
