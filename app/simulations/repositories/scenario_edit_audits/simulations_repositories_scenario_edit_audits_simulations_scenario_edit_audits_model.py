"""Application module for simulations repositories scenario edit audits simulations scenario edit audits model workflows."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base, TimestampMixin


class ScenarioEditAudit(Base, TimestampMixin):
    """Audit log row for scenario version edits."""

    __tablename__ = "scenario_edit_audit"
    __table_args__ = (
        Index(
            "ix_scenario_edit_audit_scenario_version_created_at",
            "scenario_version_id",
            "created_at",
        ),
        Index(
            "ix_scenario_edit_audit_recruiter_created_at",
            "recruiter_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_version_id: Mapped[int] = mapped_column(
        ForeignKey("scenario_versions.id"),
        nullable=False,
    )
    recruiter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    patch_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    scenario_version = relationship(
        "ScenarioVersion",
        back_populates="edit_audits",
    )
    recruiter = relationship("User")
