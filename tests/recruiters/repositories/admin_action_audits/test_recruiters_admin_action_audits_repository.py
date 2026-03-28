from __future__ import annotations

import pytest
from sqlalchemy import select

from app.recruiters.repositories.admin_action_audits import (
    AdminActionAudit,
)
from app.recruiters.repositories.admin_action_audits import (
    repository as audits_repo,
)


@pytest.mark.asyncio
async def test_create_audit_commit_true_persists_and_refreshes(async_session):
    audit = await audits_repo.create_audit(
        async_session,
        actor_type=" recruiter ",
        actor_id=" user-1 ",
        action=" reset_candidate_session ",
        target_type=" candidate_session ",
        target_id=123,
        payload_json={"reason": "manual reset"},
        commit=True,
    )

    assert audit.id.startswith("adm_")
    assert audit.actor_type == "recruiter"
    assert audit.actor_id == "user-1"
    assert audit.action == "reset_candidate_session"
    assert audit.target_type == "candidate_session"
    assert audit.target_id == "123"
    assert audit.created_at is not None

    loaded = (
        await async_session.execute(
            select(AdminActionAudit).where(AdminActionAudit.id == audit.id)
        )
    ).scalar_one_or_none()
    assert loaded is not None
    assert loaded.payload_json == {"reason": "manual reset"}
