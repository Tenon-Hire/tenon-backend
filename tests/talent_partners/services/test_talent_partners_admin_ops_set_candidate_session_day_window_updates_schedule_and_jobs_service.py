from __future__ import annotations

import pytest
from sqlalchemy import select

from app.candidates.candidate_sessions.repositories import (
    repository_day_audits as day_audits_repo,
)
from app.candidates.candidate_sessions.services.scheduling.candidates_candidate_sessions_services_scheduling_candidates_candidate_sessions_scheduling_day_windows_service import (
    derive_current_day_window,
    deserialize_day_windows,
)
from app.shared.database.shared_database_models_model import AdminActionAudit
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import Job
from app.submissions.repositories.github_native.workspaces import (
    repository as workspace_repo,
)
from tests.talent_partners.services.talent_partners_admin_ops_utils import *


@pytest.mark.asyncio
async def test_set_candidate_session_day_window_updates_schedule_and_jobs(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="day-window-owner@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="not_started",
        invite_email="candidate-day-window@test.com",
        candidate_auth0_sub="candidate:candidate-day-window@test.com",
        claimed_at=datetime(2026, 4, 3, 15, 0, tzinfo=UTC),
    )
    await async_session.commit()

    now = datetime(2026, 4, 3, 16, 30, tzinfo=UTC)
    result = await admin_ops_service.set_candidate_session_day_window(
        async_session,
        candidate_session_id=candidate_session.id,
        target_day_index=3,
        reason="  accelerate   day 3  window ",
        candidate_timezone="America/New_York",
        minutes_already_open=10,
        minutes_until_cutoff=20,
        window_start_local=None,
        window_end_local=None,
        dry_run=False,
        now=now,
    )

    assert result.status == "ok"
    assert result.audit_id is not None
    assert result.target_day_index == 3
    assert result.candidate_timezone == "America/New_York"
    assert result.current_day_window is not None
    assert result.current_day_window["dayIndex"] == 3
    assert result.current_day_window["state"] == "active"
    assert result.scheduled_start_at == datetime(2026, 4, 1, 16, 20, tzinfo=UTC)

    refreshed = await async_session.get(type(candidate_session), candidate_session.id)
    assert refreshed is not None
    assert refreshed.status == "in_progress"
    assert refreshed.started_at == now
    assert refreshed.completed_at is None
    assert refreshed.scheduled_start_at == datetime(2026, 4, 1, 16, 20, tzinfo=UTC)
    assert refreshed.candidate_timezone == "America/New_York"
    current_day_window = derive_current_day_window(
        deserialize_day_windows(refreshed.day_windows_json),
        now_utc=now,
    )
    assert current_day_window is not None
    assert current_day_window["dayIndex"] == 3
    assert current_day_window["state"] == "active"

    audit = await async_session.get(AdminActionAudit, result.audit_id)
    assert audit is not None
    assert audit.payload_json["reason"] == "accelerate day 3 window"
    assert audit.payload_json["targetDayIndex"] == 3
    assert audit.payload_json["windowStartLocal"] == "12:20"
    assert audit.payload_json["windowEndLocal"] == "12:50"

    jobs = (
        (
            await async_session.execute(
                select(Job)
                .where(Job.company_id == trial.company_id)
                .order_by(Job.job_type.asc(), Job.idempotency_key.asc())
            )
        )
        .scalars()
        .all()
    )
    assert len(jobs) == 4
    by_key = {}
    for job in jobs:
        next_run_at = job.next_run_at
        if next_run_at is not None and next_run_at.tzinfo is None:
            next_run_at = next_run_at.replace(tzinfo=UTC)
        by_key[job.idempotency_key] = next_run_at
    assert by_key[
        f"day_close_finalize_text:{candidate_session.id}:{tasks[0].id}"
    ] == datetime(2026, 4, 1, 16, 50, tzinfo=UTC)
    assert by_key[f"day_close_enforcement:{candidate_session.id}:2"] == datetime(
        2026, 4, 2, 16, 50, tzinfo=UTC
    )
    assert by_key[f"day_close_enforcement:{candidate_session.id}:3"] == datetime(
        2026, 4, 3, 16, 50, tzinfo=UTC
    )
    assert by_key[
        f"day_close_finalize_text:{candidate_session.id}:{tasks[4].id}"
    ] == datetime(2026, 4, 5, 16, 50, tzinfo=UTC)


@pytest.mark.asyncio
async def test_set_candidate_session_day_window_retimes_existing_day_audit(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="day-window-audit@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="claimed",
        invite_email="candidate-day-window-audit@test.com",
        candidate_auth0_sub="candidate:candidate-day-window-audit@test.com",
        claimed_at=datetime(2026, 4, 3, 15, 0, tzinfo=UTC),
    )
    await async_session.commit()
    await day_audits_repo.create_day_audit_once(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=3,
        cutoff_at=datetime(2026, 4, 3, 14, 0, tzinfo=UTC),
        cutoff_commit_sha="old-cutoff",
        eval_basis_ref="old-basis",
    )

    now = datetime(2026, 4, 3, 16, 30, tzinfo=UTC)
    result = await admin_ops_service.set_candidate_session_day_window(
        async_session,
        candidate_session_id=candidate_session.id,
        target_day_index=3,
        reason="retime day 3 cutoff",
        candidate_timezone="America/New_York",
        minutes_already_open=10,
        minutes_until_cutoff=20,
        window_start_local=None,
        window_end_local=None,
        dry_run=False,
        now=now,
    )

    audit = await day_audits_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=3,
    )
    assert audit is not None
    audit_cutoff = audit.cutoff_at
    if audit_cutoff.tzinfo is None:
        audit_cutoff = audit_cutoff.replace(tzinfo=UTC)
    assert audit_cutoff == result.current_day_window["windowEndAt"]
    assert audit_cutoff > now


@pytest.mark.asyncio
async def test_set_candidate_session_day_window_creates_missing_day_audit_and_retimes_workspace(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="day-window-create@test.com"
    )
    trial, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="claimed",
        invite_email="candidate-day-window-create@test.com",
        candidate_auth0_sub="candidate:candidate-day-window-create@test.com",
        claimed_at=datetime(2026, 4, 3, 15, 0, tzinfo=UTC),
        candidate_timezone="America/New_York",
    )
    workspace = await workspace_repo.create_workspace(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=tasks[2].id,
        template_repo_full_name=tasks[2].template_repo,
        repo_full_name="org/day-window-create",
        repo_id=987,
        default_branch="main",
        bootstrap_commit_sha="base-sha",
        created_at=datetime(2026, 4, 3, 15, 5, tzinfo=UTC),
        commit=False,
        refresh=False,
    )
    workspace.latest_commit_sha = "live-cutoff-sha"
    workspace.access_revoked_at = datetime(2026, 4, 3, 14, 0, tzinfo=UTC)
    await async_session.commit()

    now = datetime(2026, 4, 3, 16, 30, tzinfo=UTC)
    result = await admin_ops_service.set_candidate_session_day_window(
        async_session,
        candidate_session_id=candidate_session.id,
        target_day_index=3,
        reason="create missing day audit",
        candidate_timezone="America/New_York",
        minutes_already_open=10,
        minutes_until_cutoff=20,
        window_start_local=None,
        window_end_local=None,
        dry_run=False,
        now=now,
    )

    audit = await day_audits_repo.get_day_audit(
        async_session,
        candidate_session_id=candidate_session.id,
        day_index=3,
    )
    assert audit is not None
    audit_cutoff = audit.cutoff_at
    if audit_cutoff.tzinfo is None:
        audit_cutoff = audit_cutoff.replace(tzinfo=UTC)
    assert audit_cutoff == result.current_day_window["windowEndAt"]
    assert audit.cutoff_commit_sha == "live-cutoff-sha"
    assert audit.eval_basis_ref == "refs/heads/main@cutoff"

    refreshed_workspace = await async_session.get(type(workspace), workspace.id)
    assert refreshed_workspace is not None
    workspace_access_revoked_at = refreshed_workspace.access_revoked_at
    if workspace_access_revoked_at.tzinfo is None:
        workspace_access_revoked_at = workspace_access_revoked_at.replace(tzinfo=UTC)
    assert workspace_access_revoked_at == audit_cutoff
    assert refreshed_workspace.access_revocation_error is None
