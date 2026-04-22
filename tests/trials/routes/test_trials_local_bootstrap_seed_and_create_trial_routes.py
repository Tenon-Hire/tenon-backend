from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import (
    Base,
    CandidateSession,
    Company,
    Job,
    Trial,
    User,
    Workspace,
    WorkspaceGroup,
)
from scripts import seed_local_talent_partners as seed_local_talent_partners_script
from tests.shared.factories import (
    create_candidate_session,
    create_job,
    create_trial,
)


class _SharedSessionContext:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False


class _SharedSessionMaker:
    def __init__(self, session: AsyncSession):
        self._session = session

    def __call__(self):
        return _SharedSessionContext(self._session)


def _session_maker(async_session: AsyncSession) -> _SharedSessionMaker:
    return _SharedSessionMaker(async_session)


async def _seed_reset_proof_rows(
    async_session: AsyncSession, talent_partner: User
) -> None:
    trial, tasks = await create_trial(
        async_session,
        created_by=talent_partner,
        title="Reset Proof Trial",
    )
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="cleanup-proof@example.com",
        candidate_name="Cleanup Proof",
    )
    company = await async_session.get(Company, talent_partner.company_id)
    assert company is not None
    job = await create_job(async_session, company=company)
    group = WorkspaceGroup(
        candidate_session_id=candidate_session.id,
        workspace_key="coding",
        template_repo_full_name="org/template",
        repo_full_name="org/workspace-group",
        default_branch="main",
        base_template_sha="sha-group",
        created_at=datetime.now(UTC),
    )
    async_session.add(group)
    await async_session.flush()
    workspace = Workspace(
        workspace_group_id=group.id,
        candidate_session_id=candidate_session.id,
        task_id=tasks[0].id,
        template_repo_full_name="org/template",
        repo_full_name="org/workspace",
        repo_id=1234,
        default_branch="main",
        base_template_sha="sha-workspace",
        created_at=datetime.now(UTC),
    )
    async_session.add(workspace)
    await async_session.flush()
    assert job.id is not None


@pytest.mark.asyncio
async def test_local_bootstrap_seeds_talent_partner_and_allows_trial_creation(
    async_client,
    db_engine,
    async_session,
    monkeypatch,
):
    monkeypatch.setenv("DEV_AUTH_BYPASS", "1")
    monkeypatch.setattr(seed_local_talent_partners_script, "engine", db_engine)
    monkeypatch.setattr(
        seed_local_talent_partners_script,
        "async_session_maker",
        _session_maker(async_session),
    )

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_local_talent_partners_script.main()

    talent_partner = await async_session.scalar(
        select(User).where(User.email == "talent_partner1@local.test")
    )
    assert talent_partner is not None
    assert talent_partner.company_id is not None

    await _seed_reset_proof_rows(async_session, talent_partner)
    await async_session.commit()

    response = await async_client.post(
        "/api/trials",
        headers={"x-dev-user-email": talent_partner.email},
        json={
            "title": "Local Trial",
            "role": "Backend Engineer",
            "seniority": "Mid",
            "preferredLanguageFramework": "Python, PostgreSQL",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["title"] == "Local Trial"
    assert response.json()["techStack"] == "Python, PostgreSQL"
    assert response.json()["companyContext"]["preferredLanguageFramework"] == (
        "Python, PostgreSQL"
    )

    async_session.expunge_all()
    await seed_local_talent_partners_script.main(reset=True)

    async_session.expire_all()
    reset_talent_partner = await async_session.scalar(
        select(User).where(User.email == "talent_partner1@local.test")
    )
    reset_trial = await async_session.scalar(
        select(Trial).where(Trial.title == "Local Trial")
    )
    reset_candidate_session = await async_session.scalar(
        select(CandidateSession).where(
            CandidateSession.invite_email == "cleanup-proof@example.com"
        )
    )
    reset_job = await async_session.scalar(
        select(Job).where(Job.company_id == talent_partner.company_id)
    )
    reset_workspace = await async_session.scalar(
        select(Workspace).where(Workspace.repo_full_name == "org/workspace")
    )
    reset_workspace_group = await async_session.scalar(
        select(WorkspaceGroup).where(
            WorkspaceGroup.repo_full_name == "org/workspace-group"
        )
    )
    assert reset_talent_partner is not None
    assert reset_talent_partner.company_id is not None
    assert reset_trial is None
    assert reset_candidate_session is None
    assert reset_job is None
    assert reset_workspace is None
    assert reset_workspace_group is None
