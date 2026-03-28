from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_jobs_repository_access_and_recovery(async_session, monkeypatch):
    company = await create_company(async_session, name="Jobs Branch Co")
    company_id = company.id
    original_load_idempotent_job = jobs_repo._load_idempotent_job
    existing = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="branch_job",
        idempotency_key="branch-key",
        payload_json={"a": 1},
        company_id=company_id,
    )
    existing_id = existing.id

    candidate_principal = SimpleNamespace(
        permissions=["candidate:access"],
        claims={"email_verified": True},
        email=" ",
        sub="candidate-sub",
    )
    assert (
        await jobs_repo.get_by_id_for_principal(
            async_session, existing_id, candidate_principal
        )
        is None
    )
    no_access_principal = SimpleNamespace(
        permissions=["viewer"],
        claims={},
        email="viewer@example.com",
        sub="viewer-sub",
    )
    assert (
        await jobs_repo.get_by_id_for_principal(
            async_session, existing_id, no_access_principal
        )
        is None
    )

    spec = jobs_repo.IdempotentJobSpec(
        job_type="spec_type",
        idempotency_key="spec-key",
        payload_json={"v": 1},
    )
    job_from_spec = jobs_repo._job_from_spec(company_id=company_id, spec=spec)
    assert job_from_spec.job_type == "spec_type"
    assert job_from_spec.idempotency_key == "spec-key"
    assert (
        await jobs_repo._load_idempotent_jobs_for_keys(
            async_session, company_id=company_id, keys=[]
        )
        == {}
    )

    async def _load_none(*_args, **_kwargs):
        return None

    monkeypatch.setattr(jobs_repo, "_load_idempotent_job", _load_none)
    with pytest.raises(IntegrityError):
        await jobs_repo.create_or_get_idempotent(
            async_session,
            job_type="branch_job",
            idempotency_key="branch-key",
            payload_json={"a": 2},
            company_id=company_id,
            commit=False,
        )

    calls = {"count": 0}

    async def _load_side_effect(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return None
        return SimpleNamespace(id=existing_id)

    monkeypatch.setattr(jobs_repo, "_load_idempotent_job", _load_side_effect)
    recovered = await jobs_repo.create_or_get_idempotent(
        async_session,
        job_type="branch_job",
        idempotency_key="branch-key",
        payload_json={"a": 3},
        company_id=company_id,
        commit=True,
    )
    assert recovered.id == existing_id
    monkeypatch.setattr(jobs_repo, "_load_idempotent_job", original_load_idempotent_job)
