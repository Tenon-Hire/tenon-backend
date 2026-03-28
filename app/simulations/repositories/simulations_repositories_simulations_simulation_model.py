"""Application module for simulations repositories simulations simulation model workflows."""

from datetime import datetime, time

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    false,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base, TimestampMixin
from app.simulations.constants.simulations_constants_simulations_ai_config_constants import (
    AI_EVAL_ENABLED_BY_DAY_DEFAULT_JSON,
    AI_NOTICE_DEFAULT_TEXT,
    AI_NOTICE_DEFAULT_VERSION,
    default_ai_eval_enabled_by_day,
)
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    DEFAULT_TEMPLATE_KEY,
)

from .simulations_repositories_simulations_simulation_status_constants import (
    LEGACY_SIMULATION_STATUS_ACTIVE,
    SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME,
    SIMULATION_STATUS_ACTIVE_INVITING,
    SIMULATION_STATUS_CHECK_CONSTRAINT_NAME,
    SIMULATION_STATUS_DRAFT,
    SIMULATION_STATUS_GENERATING,
    SIMULATION_STATUS_READY_FOR_REVIEW,
    SIMULATION_STATUS_TERMINATED,
    SIMULATION_STATUSES,
    _active_scenario_required_expr,
    _status_check_expr,
)


class Simulation(Base, TimestampMixin):
    """Simulation configuration assigned to candidates."""

    __tablename__ = "simulations"
    __table_args__ = (
        CheckConstraint(
            _status_check_expr(), name=SIMULATION_STATUS_CHECK_CONSTRAINT_NAME
        ),
        CheckConstraint(
            _active_scenario_required_expr(),
            name=SIMULATION_ACTIVE_SCENARIO_REQUIRED_CHECK_NAME,
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
    ai_notice_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=AI_NOTICE_DEFAULT_VERSION,
        server_default=AI_NOTICE_DEFAULT_VERSION,
    )
    ai_notice_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=AI_NOTICE_DEFAULT_TEXT,
        server_default=AI_NOTICE_DEFAULT_TEXT,
    )
    ai_eval_enabled_by_day: Mapped[dict[str, bool]] = mapped_column(
        JSON,
        nullable=False,
        default=default_ai_eval_enabled_by_day,
        server_default=text(f"'{AI_EVAL_ENABLED_BY_DAY_DEFAULT_JSON}'"),
    )
    day_window_start_local: Mapped[time] = mapped_column(
        Time(),
        default=time(hour=9, minute=0),
        server_default=text("'09:00:00'"),
        nullable=False,
    )
    day_window_end_local: Mapped[time] = mapped_column(
        Time(),
        default=time(hour=17, minute=0),
        server_default=text("'17:00:00'"),
        nullable=False,
    )
    day_window_overrides_enabled: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default=false(), nullable=False
    )
    day_window_overrides_json: Mapped[dict[str, dict[str, str]] | None] = mapped_column(
        JSON, nullable=True
    )

    active_scenario_version_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "scenario_versions.id",
            use_alter=True,
            name="fk_simulations_active_scenario_version_id",
        ),
        nullable=True,
    )
    pending_scenario_version_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "scenario_versions.id",
            use_alter=True,
            name="fk_simulations_pending_scenario_version_id",
        ),
        nullable=True,
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
    scenario_versions = relationship(
        "ScenarioVersion",
        back_populates="simulation",
        foreign_keys="ScenarioVersion.simulation_id",
    )
    active_scenario_version = relationship(
        "ScenarioVersion",
        foreign_keys=[active_scenario_version_id],
        uselist=False,
        post_update=True,
    )
    pending_scenario_version = relationship(
        "ScenarioVersion",
        foreign_keys=[pending_scenario_version_id],
        uselist=False,
        post_update=True,
    )
    candidate_sessions = relationship("CandidateSession", back_populates="simulation")


__all__ = [
    "LEGACY_SIMULATION_STATUS_ACTIVE",
    "SIMULATION_STATUSES",
    "SIMULATION_STATUS_ACTIVE_INVITING",
    "SIMULATION_STATUS_DRAFT",
    "SIMULATION_STATUS_GENERATING",
    "SIMULATION_STATUS_READY_FOR_REVIEW",
    "SIMULATION_STATUS_TERMINATED",
    "Simulation",
]
