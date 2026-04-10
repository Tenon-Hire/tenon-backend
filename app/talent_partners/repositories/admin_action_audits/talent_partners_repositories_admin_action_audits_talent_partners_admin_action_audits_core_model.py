"""Application module for Talent Partners repositories admin action audits Talent Partners admin action audits core model workflows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.shared_database_base_model import Base


def _audit_id() -> str:
    return f"adm_{uuid.uuid4().hex}"


class AdminActionAudit(Base):
    """Audit record for admin demo-ops actions."""

    __tablename__ = "admin_action_audits"
    __table_args__ = (
        Index("ix_admin_action_audits_created_at", "created_at"),
        Index("ix_admin_action_audits_action_created_at", "action", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=_audit_id)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
