"""Application module for evaluations repositories rubric snapshot model workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base

RUBRIC_SNAPSHOT_SCOPE_WINOE = "winoe"
RUBRIC_SNAPSHOT_SCOPE_COMPANY = "company"
RUBRIC_SNAPSHOT_SCOPES = (
    RUBRIC_SNAPSHOT_SCOPE_WINOE,
    RUBRIC_SNAPSHOT_SCOPE_COMPANY,
)


def _scope_check_expr() -> str:
    allowed = ",".join(f"'{scope}'" for scope in RUBRIC_SNAPSHOT_SCOPES)
    return f"scope IN ({allowed})"


class WinoeRubricSnapshot(Base):
    """Immutable rubric snapshot materialized for one scenario version."""

    __tablename__ = "winoe_rubric_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "scenario_version_id",
            "scope",
            "rubric_kind",
            "rubric_key",
            "rubric_version",
            name="uq_winoe_rubric_snapshots_scenario_scope_kind_key_version",
        ),
        CheckConstraint(
            _scope_check_expr(),
            name="ck_winoe_rubric_snapshots_scope",
        ),
        Index(
            "ix_winoe_rubric_snapshots_scenario_version_id",
            "scenario_version_id",
        ),
        Index("ix_winoe_rubric_snapshots_scope", "scope"),
        Index("ix_winoe_rubric_snapshots_rubric_kind", "rubric_kind"),
        Index("ix_winoe_rubric_snapshots_rubric_key", "rubric_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_version_id: Mapped[int] = mapped_column(
        ForeignKey("scenario_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    rubric_kind: Mapped[str] = mapped_column(String(100), nullable=False)
    rubric_key: Mapped[str] = mapped_column(String(100), nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    scenario_version = relationship(
        "ScenarioVersion", back_populates="rubric_snapshots"
    )


__all__ = [
    "RUBRIC_SNAPSHOT_SCOPE_COMPANY",
    "RUBRIC_SNAPSHOT_SCOPE_WINOE",
    "RUBRIC_SNAPSHOT_SCOPES",
    "WinoeRubricSnapshot",
]
