"""Application module for simulations repositories scenario versions simulations scenario versions model workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base, TimestampMixin

SCENARIO_VERSION_STATUS_DRAFT = "draft"
SCENARIO_VERSION_STATUS_GENERATING = "generating"
SCENARIO_VERSION_STATUS_READY = "ready"
SCENARIO_VERSION_STATUS_LOCKED = "locked"
SCENARIO_VERSION_STATUSES = (
    SCENARIO_VERSION_STATUS_DRAFT,
    SCENARIO_VERSION_STATUS_GENERATING,
    SCENARIO_VERSION_STATUS_READY,
    SCENARIO_VERSION_STATUS_LOCKED,
)
SCENARIO_VERSION_STATUS_CHECK_CONSTRAINT_NAME = "ck_scenario_versions_status"


def _status_check_expr() -> str:
    allowed = ",".join(f"'{status}'" for status in SCENARIO_VERSION_STATUSES)
    return f"status IN ({allowed})"


class ScenarioVersion(Base, TimestampMixin):
    """Represent scenario version data and behavior."""

    __tablename__ = "scenario_versions"
    __table_args__ = (
        UniqueConstraint(
            "simulation_id",
            "version_index",
            name="uq_scenario_versions_simulation_version_index",
        ),
        CheckConstraint(
            _status_check_expr(),
            name=SCENARIO_VERSION_STATUS_CHECK_CONSTRAINT_NAME,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    simulation_id: Mapped[int] = mapped_column(
        ForeignKey("simulations.id"),
        nullable=False,
    )
    version_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SCENARIO_VERSION_STATUS_DRAFT,
    )
    storyline_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    task_prompts_json: Mapped[dict | list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    rubric_json: Mapped[dict | list] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    focus_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    template_key: Mapped[str] = mapped_column(String(255), nullable=False)
    tech_stack: Mapped[str] = mapped_column(String(255), nullable=False)
    seniority: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rubric_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    simulation = relationship(
        "Simulation", back_populates="scenario_versions", foreign_keys=[simulation_id]
    )
    candidate_sessions = relationship(
        "CandidateSession", back_populates="scenario_version"
    )
    edit_audits = relationship(
        "ScenarioEditAudit",
        back_populates="scenario_version",
        cascade="all, delete-orphan",
    )
    precommit_bundles = relationship(
        "PrecommitBundle",
        back_populates="scenario_version",
        cascade="all, delete-orphan",
    )
