from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base, TimestampMixin
from app.services.tasks.template_catalog import DEFAULT_TEMPLATE_KEY

SIMULATION_STATUS_DRAFT = "draft"
SIMULATION_STATUS_GENERATING = "generating"
SIMULATION_STATUS_READY_FOR_REVIEW = "ready_for_review"
SIMULATION_STATUS_ACTIVE_INVITING = "active_inviting"
SIMULATION_STATUS_TERMINATED = "terminated"

SIMULATION_STATUSES = (
    SIMULATION_STATUS_DRAFT,
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_TERMINATED,
)

LEGACY_SIMULATION_STATUS_ACTIVE = "active"
SIMULATION_STATUS_CHECK_CONSTRAINT_NAME = "ck_simulations_status_lifecycle"


def _status_check_expr() -> str:
    allowed = ",".join(f"'{status}'" for status in SIMULATION_STATUSES)
    return f"status IN ({allowed})"


class Simulation(Base, TimestampMixin):
    """Simulation configuration assigned to candidates."""

    __tablename__ = "simulations"
    __table_args__ = (
        CheckConstraint(
            _status_check_expr(),
            name=SIMULATION_STATUS_CHECK_CONSTRAINT_NAME,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    title: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(255))
    tech_stack: Mapped[str] = mapped_column(String(255))
    seniority: Mapped[str] = mapped_column(String(100))
    scenario_template: Mapped[str] = mapped_column(String(255))
    template_key: Mapped[str] = mapped_column(
        String(255),
        default=DEFAULT_TEMPLATE_KEY,
        server_default=DEFAULT_TEMPLATE_KEY,
        nullable=False,
    )

    focus: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="", default=""
    )
    company_context: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    ai_notice_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_notice_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_eval_enabled_by_day: Mapped[dict[str, bool] | None] = mapped_column(
        JSON, nullable=True
    )

    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(
        String(50),
        default=SIMULATION_STATUS_GENERATING,
        server_default=SIMULATION_STATUS_GENERATING,
        nullable=False,
    )
    generating_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ready_for_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terminated_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    terminated_by_recruiter_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    company = relationship("Company", back_populates="simulations")
    tasks = relationship("Task", back_populates="simulation")
    candidate_sessions = relationship("CandidateSession", back_populates="simulation")
