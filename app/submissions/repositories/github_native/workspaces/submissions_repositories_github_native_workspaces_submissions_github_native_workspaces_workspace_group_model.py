"""Application module for submissions repositories github native workspaces submissions github native workspaces workspace group model workflows."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.shared_database_base_model import Base


class WorkspaceGroup(Base):
    """Canonical workspace repo metadata shared across related coding tasks."""

    __tablename__ = "workspace_groups"
    __table_args__ = (
        UniqueConstraint(
            "candidate_session_id",
            "workspace_key",
            name="uq_workspace_groups_session_key",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    candidate_session_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_sessions.id", ondelete="CASCADE"), nullable=False
    )
    workspace_key: Mapped[str] = mapped_column(String(64), nullable=False)
    template_repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str | None] = mapped_column(String(120), nullable=True)
    base_template_sha: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cleanup_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cleanup_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cleaned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cleanup_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_revocation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    candidate_session = relationship(
        "CandidateSession", back_populates="workspace_groups"
    )
    workspaces = relationship(
        "Workspace", back_populates="workspace_group", cascade="all, delete-orphan"
    )
