"""Application module for Talent Partners repositories admin action audits Talent Partners admin action audits core repository workflows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.talent_partners.repositories.admin_action_audits.talent_partners_repositories_admin_action_audits_talent_partners_admin_action_audits_core_model import (
    AdminActionAudit,
)


async def create_audit(
    db: AsyncSession,
    *,
    actor_type: str,
    actor_id: str,
    action: str,
    target_type: str,
    target_id: str | int,
    payload_json: Mapping[str, Any],
    commit: bool = False,
) -> AdminActionAudit:
    """Create audit."""
    audit = AdminActionAudit(
        actor_type=actor_type.strip(),
        actor_id=str(actor_id).strip(),
        action=action.strip(),
        target_type=target_type.strip(),
        target_id=str(target_id).strip(),
        payload_json=dict(payload_json),
    )
    db.add(audit)
    if commit:
        await db.commit()
        await db.refresh(audit)
    else:
        await db.flush()
    return audit


__all__ = ["create_audit"]
