from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
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


class Simulation(Base, TimestampMixin):
    """Simulation configuration assigned to candidates."""

    __tablename__ = "simulations"

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

    company = relationship("Company", back_populates="simulations")
    tasks = relationship("Task", back_populates="simulation")
    candidate_sessions = relationship("CandidateSession", back_populates="simulation")
