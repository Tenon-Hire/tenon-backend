from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import Base

WORKSPACE_CLEANUP_STATUS_PENDING = "pending"
WORKSPACE_CLEANUP_STATUS_ARCHIVED = "archived"
WORKSPACE_CLEANUP_STATUS_DELETED = "deleted"
WORKSPACE_CLEANUP_STATUS_FAILED = "failed"
WORKSPACE_CLEANUP_TERMINAL_STATUSES = {
    WORKSPACE_CLEANUP_STATUS_ARCHIVED,
    WORKSPACE_CLEANUP_STATUS_DELETED,
}


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


class Workspace(Base):
    """GitHub workspace repository provisioned for a candidate task."""

    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint(
            "candidate_session_id", "task_id", name="uq_workspaces_session_task"
        ),
        UniqueConstraint("workspace_group_id", name="uq_workspaces_workspace_group_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_group_id: Mapped[str | None] = mapped_column(
        ForeignKey("workspace_groups.id", ondelete="CASCADE"), nullable=True
    )
    candidate_session_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_sessions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    template_repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(120), nullable=True)
    base_template_sha: Mapped[str | None] = mapped_column(String(100), nullable=True)
    precommit_sha: Mapped[str | None] = mapped_column(String(100), nullable=True)
    precommit_details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    latest_commit_sha: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_workflow_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_workflow_conclusion: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    last_test_summary_json: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # JSON string with counts/output
    codespace_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    codespace_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    codespace_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
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

    candidate_session = relationship("CandidateSession", back_populates="workspaces")
    task = relationship("Task", back_populates="workspaces")
    workspace_group = relationship("WorkspaceGroup", back_populates="workspaces")
