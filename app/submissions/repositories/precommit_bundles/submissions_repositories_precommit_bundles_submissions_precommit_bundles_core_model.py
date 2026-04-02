"""Application module for submissions repositories precommit bundles submissions precommit bundles core model workflows."""

from __future__ import annotations

from datetime import datetime

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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.shared.database.shared_database_base_model import Base

PRECOMMIT_BUNDLE_STATUS_GENERATING = "generating"
PRECOMMIT_BUNDLE_STATUS_READY = "ready"
PRECOMMIT_BUNDLE_STATUS_FAILED = "failed"
PRECOMMIT_BUNDLE_STATUS_DISABLED = "disabled"
PRECOMMIT_BUNDLE_STATUS_DRAFT = PRECOMMIT_BUNDLE_STATUS_GENERATING
PRECOMMIT_BUNDLE_STATUSES = (
    PRECOMMIT_BUNDLE_STATUS_GENERATING,
    PRECOMMIT_BUNDLE_STATUS_READY,
    PRECOMMIT_BUNDLE_STATUS_FAILED,
    PRECOMMIT_BUNDLE_STATUS_DISABLED,
)
PRECOMMIT_BUNDLE_STATUS_CHECK_CONSTRAINT_NAME = "ck_precommit_bundles_status"
PRECOMMIT_BUNDLE_UNIQUE_CONSTRAINT_NAME = "uq_precommit_bundles_scenario_template"
PRECOMMIT_BUNDLE_CONTENT_REQUIRED_CONSTRAINT_NAME = "ck_precommit_bundle_content_source"


def _status_check_expr() -> str:
    allowed = ",".join(f"'{status}'" for status in PRECOMMIT_BUNDLE_STATUSES)
    return f"status IN ({allowed})"


def _content_required_expr() -> str:
    return (
        "(status != 'ready') OR (patch_text IS NOT NULL) OR (storage_ref IS NOT NULL)"
    )


class PrecommitBundle(Base):
    """Represent precommit bundle data and behavior."""

    __tablename__ = "precommit_bundles"
    __table_args__ = (
        UniqueConstraint(
            "scenario_version_id",
            "template_key",
            name=PRECOMMIT_BUNDLE_UNIQUE_CONSTRAINT_NAME,
        ),
        CheckConstraint(
            _status_check_expr(),
            name=PRECOMMIT_BUNDLE_STATUS_CHECK_CONSTRAINT_NAME,
        ),
        CheckConstraint(
            _content_required_expr(),
            name=PRECOMMIT_BUNDLE_CONTENT_REQUIRED_CONSTRAINT_NAME,
        ),
        Index(
            "ix_precommit_bundles_lookup",
            "scenario_version_id",
            "template_key",
            "status",
        ),
        Index(
            "ix_precommit_bundles_scenario_version_id",
            "scenario_version_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_version_id: Mapped[int] = mapped_column(
        ForeignKey("scenario_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PRECOMMIT_BUNDLE_STATUS_GENERATING,
    )
    patch_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_template_sha: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Internal provenance pointer for the canonical bundle artifact source commit.
    # Candidate workspace specialization commits are stored on Workspace.precommit_sha.
    applied_commit_sha: Mapped[str | None] = mapped_column(String(100), nullable=True)
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    test_summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provenance_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    scenario_version = relationship(
        "ScenarioVersion", back_populates="precommit_bundles"
    )
