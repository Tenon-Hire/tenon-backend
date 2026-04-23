"""Application module for evaluations repositories reviewer report model workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base

from .evaluations_repositories_evaluations_constants_model import (
    EVALUATION_REVIEWER_REPORT_DAY_INDEX_CHECK_CONSTRAINT_NAME,
    EVALUATION_REVIEWER_REPORT_RUN_AGENT_DAY_UNIQUE_CONSTRAINT_NAME,
)


class EvaluationReviewerReport(Base):
    """Structured reviewer sub-report for one day and reviewer agent."""

    __tablename__ = "evaluation_reviewer_reports"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "reviewer_agent_key",
            "day_index",
            name=EVALUATION_REVIEWER_REPORT_RUN_AGENT_DAY_UNIQUE_CONSTRAINT_NAME,
        ),
        CheckConstraint(
            "day_index BETWEEN 1 AND 5",
            name=EVALUATION_REVIEWER_REPORT_DAY_INDEX_CHECK_CONSTRAINT_NAME,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reviewer_agent_key: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    submission_kind: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    dimensional_scores_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    evidence_citations_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    assessment_text: Mapped[str] = mapped_column(Text, nullable=False)
    strengths_json: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    risks_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    raw_output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run = relationship("EvaluationRun", back_populates="reviewer_reports")
