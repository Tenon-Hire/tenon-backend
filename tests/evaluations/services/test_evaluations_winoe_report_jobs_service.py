from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_jobs_service as winoe_report_jobs,
)


def test_build_evaluation_job_idempotency_key_is_stable():
    assert (
        winoe_report_jobs.build_evaluation_job_idempotency_key(
            basis_fingerprint="basis-42"
        )
        == "evaluation_run:basis-42"
    )


@pytest.mark.asyncio
async def test_enqueue_evaluation_run_uses_retry_budget(monkeypatch) -> None:
    observed: dict[str, object] = {}

    async def _create_or_get_idempotent(db, **kwargs):
        observed.update(kwargs)
        return SimpleNamespace(id="job-1", payload_json={})

    db = SimpleNamespace(flush=AsyncMock())
    monkeypatch.setattr(
        winoe_report_jobs.jobs_repo,
        "create_or_get_idempotent",
        _create_or_get_idempotent,
    )

    result = await winoe_report_jobs.enqueue_evaluation_run(
        db,
        candidate_session_id=42,
        company_id=7,
        requested_by_user_id=9,
        basis_fingerprint="basis-42",
        commit=False,
    )

    assert result.id == "job-1"
    assert observed["max_attempts"] == winoe_report_jobs.EVALUATION_RUN_JOB_MAX_ATTEMPTS
    assert observed["candidate_session_id"] == 42
    assert observed["payload_json"]["basisFingerprint"] == "basis-42"
    assert observed["idempotency_key"] == "evaluation_run:basis-42"
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_enqueue_evaluation_run_commits_and_refreshes_when_requested(
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}

    async def _create_or_get_idempotent(db, **kwargs):
        observed.update(kwargs)
        return SimpleNamespace(id="job-2", payload_json={})

    db = SimpleNamespace(commit=AsyncMock(), refresh=AsyncMock(), flush=AsyncMock())
    monkeypatch.setattr(
        winoe_report_jobs.jobs_repo,
        "create_or_get_idempotent",
        _create_or_get_idempotent,
    )

    result = await winoe_report_jobs.enqueue_evaluation_run(
        db,
        candidate_session_id=7,
        company_id=11,
        requested_by_user_id=13,
        basis_fingerprint="basis-7",
        commit=True,
    )

    assert result.id == "job-2"
    assert observed["company_id"] == 11
    assert observed["idempotency_key"] == "evaluation_run:basis-7"
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_enqueue_evaluation_run_reuses_job_for_same_basis(monkeypatch) -> None:
    jobs_by_key: dict[str, SimpleNamespace] = {}
    created_keys: list[str] = []

    async def _create_or_get_idempotent(db, **kwargs):
        key = kwargs["idempotency_key"]
        created_keys.append(key)
        job = jobs_by_key.get(key)
        if job is None:
            job = SimpleNamespace(
                id=f"job-{len(jobs_by_key) + 1}",
                payload_json=dict(kwargs["payload_json"]),
            )
            jobs_by_key[key] = job
        return job

    db = SimpleNamespace(flush=AsyncMock())
    monkeypatch.setattr(
        winoe_report_jobs.jobs_repo,
        "create_or_get_idempotent",
        _create_or_get_idempotent,
    )

    first = await winoe_report_jobs.enqueue_evaluation_run(
        db,
        candidate_session_id=12,
        company_id=34,
        requested_by_user_id=56,
        basis_fingerprint="basis-same",
        commit=False,
    )
    second = await winoe_report_jobs.enqueue_evaluation_run(
        db,
        candidate_session_id=12,
        company_id=34,
        requested_by_user_id=56,
        basis_fingerprint="basis-same",
        commit=False,
    )

    assert first.id == second.id
    assert created_keys == ["evaluation_run:basis-same", "evaluation_run:basis-same"]
    assert first.payload_json["jobId"] == first.id
    assert second.payload_json["jobId"] == second.id


@pytest.mark.asyncio
async def test_enqueue_evaluation_run_creates_new_job_for_changed_basis(monkeypatch):
    jobs_by_key: dict[str, SimpleNamespace] = {}

    async def _create_or_get_idempotent(db, **kwargs):
        key = kwargs["idempotency_key"]
        job = jobs_by_key.get(key)
        if job is None:
            job = SimpleNamespace(
                id=f"job-{len(jobs_by_key) + 1}",
                payload_json=dict(kwargs["payload_json"]),
            )
            jobs_by_key[key] = job
        return job

    db = SimpleNamespace(flush=AsyncMock())
    monkeypatch.setattr(
        winoe_report_jobs.jobs_repo,
        "create_or_get_idempotent",
        _create_or_get_idempotent,
    )

    first = await winoe_report_jobs.enqueue_evaluation_run(
        db,
        candidate_session_id=12,
        company_id=34,
        requested_by_user_id=56,
        basis_fingerprint="basis-old",
        commit=False,
    )
    second = await winoe_report_jobs.enqueue_evaluation_run(
        db,
        candidate_session_id=12,
        company_id=34,
        requested_by_user_id=56,
        basis_fingerprint="basis-new",
        commit=False,
    )

    assert first.id != second.id
    assert first.payload_json["jobId"] == first.id
    assert second.payload_json["jobId"] == second.id
