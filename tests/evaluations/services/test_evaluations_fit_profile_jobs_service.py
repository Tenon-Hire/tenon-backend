from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.evaluations.services import (
    evaluations_services_evaluations_fit_profile_jobs_service as fit_profile_jobs,
)


def test_build_evaluation_job_payload_shape():
    payload = fit_profile_jobs.build_evaluation_job_payload(
        candidate_session_id=123,
        company_id=456,
        requested_by_user_id=789,
    )
    assert payload["candidateSessionId"] == 123
    assert payload["companyId"] == 456
    assert payload["requestedByUserId"] == 789
    assert isinstance(payload["requestedAt"], str)
    assert payload["requestedAt"].endswith("Z")

    parsed = datetime.fromisoformat(str(payload["requestedAt"]).replace("Z", "+00:00"))
    assert parsed.tzinfo == UTC


def test_build_evaluation_job_idempotency_key_is_unique_per_request():
    key_one = fit_profile_jobs.build_evaluation_job_idempotency_key(321)
    key_two = fit_profile_jobs.build_evaluation_job_idempotency_key(321)

    assert key_one != key_two
    assert key_one.startswith("evaluation_run:321:")
    assert key_two.startswith("evaluation_run:321:")
    assert len(key_one.split(":")[-1]) == 32


@pytest.mark.asyncio
async def test_enqueue_evaluation_run_commit_true(monkeypatch):
    created = SimpleNamespace(id="job-1", payload_json={"candidateSessionId": 11})
    create_or_get = AsyncMock(return_value=created)
    monkeypatch.setattr(
        fit_profile_jobs.jobs_repo,
        "create_or_get_idempotent",
        create_or_get,
    )

    db = SimpleNamespace(
        commit=AsyncMock(),
        refresh=AsyncMock(),
        flush=AsyncMock(),
    )

    job = await fit_profile_jobs.enqueue_evaluation_run(
        db,
        candidate_session_id=11,
        company_id=22,
        requested_by_user_id=33,
        commit=True,
    )

    assert job is created
    assert created.payload_json["jobId"] == "job-1"
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(created)
    db.flush.assert_not_awaited()
    create_or_get.assert_awaited_once()


@pytest.mark.asyncio
async def test_enqueue_evaluation_run_commit_false(monkeypatch):
    created = SimpleNamespace(id="job-2", payload_json={})
    monkeypatch.setattr(
        fit_profile_jobs.jobs_repo,
        "create_or_get_idempotent",
        AsyncMock(return_value=created),
    )
    db = SimpleNamespace(
        commit=AsyncMock(),
        refresh=AsyncMock(),
        flush=AsyncMock(),
    )

    job = await fit_profile_jobs.enqueue_evaluation_run(
        db,
        candidate_session_id=99,
        company_id=77,
        requested_by_user_id=55,
        commit=False,
    )

    assert job is created
    assert created.payload_json["jobId"] == "job-2"
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()
    db.refresh.assert_not_awaited()
