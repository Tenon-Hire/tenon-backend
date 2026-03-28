"""Application module for evaluations repositories evaluations day score model workflows."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base

from .evaluations_repositories_evaluations_constants_model import (
    EVALUATION_DAY_SCORE_DAY_INDEX_CHECK_CONSTRAINT_NAME,
    EVALUATION_DAY_SCORE_RUN_DAY_UNIQUE_CONSTRAINT_NAME,
)


class EvaluationDayScore(Base):
    """Per-day scoring + rubric output + evidence pointers."""

    __tablename__ = "evaluation_day_scores"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "day_index",
            name=EVALUATION_DAY_SCORE_RUN_DAY_UNIQUE_CONSTRAINT_NAME,
        ),
        CheckConstraint(
            "day_index BETWEEN 1 AND 5",
            name=EVALUATION_DAY_SCORE_DAY_INDEX_CHECK_CONSTRAINT_NAME,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    rubric_results_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    evidence_pointers_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run = relationship("EvaluationRun", back_populates="day_scores")
