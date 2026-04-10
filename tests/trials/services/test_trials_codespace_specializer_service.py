from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials.services import (
    trials_services_trials_codespace_specializer_service as specializer_service,
)


async def test_enqueue_codespace_specializer_job_uses_retry_budget(
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}

    async def _create_or_get_idempotent(db, **kwargs):
        observed.update(kwargs)
        return SimpleNamespace(id="job-1")

    monkeypatch.setattr(
        specializer_service.jobs_repo,
        "create_or_get_idempotent",
        _create_or_get_idempotent,
    )

    result = await specializer_service.enqueue_codespace_specializer_job(
        db=object(),
        trial_id=25,
        scenario_version_id=20,
        company_id=7,
        commit=False,
    )

    assert result.id == "job-1"
    assert (
        observed["max_attempts"]
        == specializer_service.CODESPACE_SPECIALIZER_JOB_MAX_ATTEMPTS
    )
    assert observed["idempotency_key"] == "scenario:20:codespace_specializer"


def test_codespace_job_has_retry_headroom_requires_nonterminal_retry_state() -> None:
    assert specializer_service._codespace_job_has_retry_headroom(
        SimpleNamespace(status="queued", attempt=2, max_attempts=7)
    )
    assert specializer_service._codespace_job_has_retry_headroom(
        SimpleNamespace(status="running", attempt=6, max_attempts=7)
    )
    assert not specializer_service._codespace_job_has_retry_headroom(
        SimpleNamespace(status="queued", attempt=7, max_attempts=7)
    )
    assert not specializer_service._codespace_job_has_retry_headroom(
        SimpleNamespace(status="dead_letter", attempt=2, max_attempts=7)
    )


async def test_ensure_precommit_bundle_ready_for_invites_treats_retrying_bundle_as_not_ready(
    monkeypatch,
) -> None:
    class _Db:
        async def commit(self) -> None:
            return None

    async def _get_ready(*_args, **_kwargs):
        return None

    async def _get_existing(*_args, **_kwargs):
        return SimpleNamespace(
            status="failed",
            last_error="openai_request_failed:RateLimitError",
        )

    async def _load_job(*_args, **_kwargs):
        return SimpleNamespace(status="queued", attempt=2, max_attempts=7)

    monkeypatch.setattr(
        specializer_service.bundle_lookup_repo,
        "get_ready_by_scenario_and_template",
        _get_ready,
    )
    monkeypatch.setattr(
        specializer_service.bundle_lookup_repo,
        "get_by_scenario_and_template",
        _get_existing,
    )
    monkeypatch.setattr(specializer_service, "load_idempotent_job", _load_job)

    with pytest.raises(ApiError) as exc_info:
        await specializer_service.ensure_precommit_bundle_ready_for_invites(
            db=_Db(),
            trial=SimpleNamespace(company_id=7),
            scenario_version=SimpleNamespace(id=21, template_key="python-fastapi"),
            tasks=[SimpleNamespace(day_index=2, type="code")],
        )

    exc = exc_info.value
    assert exc.error_code == "PRECOMMIT_BUNDLE_NOT_READY"
    assert exc.retryable is True
    assert exc.details["bundleStatus"] == "generating"
    assert exc.details["jobStatus"] == "queued"


async def test_run_codespace_specializer_job_degrades_to_context_bundle_after_retryable_provider_failures(
    monkeypatch,
) -> None:
    trial = SimpleNamespace(id=31, company_id=7)
    scenario_version = SimpleNamespace(
        id=24,
        trial_id=31,
        status="locked",
        template_key="python-fastapi",
        ai_policy_snapshot_json={"agents": {"codespace": {"runtime": {}}}},
    )
    tasks = [
        SimpleNamespace(
            trial_id=31,
            day_index=2,
            type="code",
            template_repo="acme/python-fastapi-template",
        )
    ]
    existing_bundle = SimpleNamespace(
        id=88,
        status="generating",
        last_error=None,
    )

    class _ScalarResult:
        def __init__(self, value):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _ScalarsResult:
        def __init__(self, values):
            self._values = values

        def scalars(self):
            return self

        def all(self):
            return self._values

    class _Db:
        def __init__(self):
            self.execute_calls = 0
            self.commits = 0
            self.refreshed: list[int] = []

        async def execute(self, _stmt):
            self.execute_calls += 1
            if self.execute_calls == 1:
                return _ScalarResult(trial)
            if self.execute_calls == 2:
                return _ScalarResult(scenario_version)
            return _ScalarsResult(tasks)

        async def commit(self) -> None:
            self.commits += 1

        async def refresh(self, bundle) -> None:
            self.refreshed.append(bundle.id)

    update_calls: list[dict[str, object]] = []

    async def _get_bundle(*_args, **_kwargs):
        return existing_bundle

    async def _update_bundle(_db, *, bundle, **kwargs):
        update_calls.append(kwargs)
        for key, value in kwargs.items():
            if key != "commit":
                setattr(bundle, key, value)
        return bundle

    monkeypatch.setattr(
        specializer_service.bundle_lookup_repo,
        "get_by_scenario_and_template",
        _get_bundle,
    )
    monkeypatch.setattr(
        specializer_service.bundle_write_repo,
        "update_bundle",
        _update_bundle,
    )
    monkeypatch.setattr(
        specializer_service,
        "require_agent_runtime",
        lambda *_args, **_kwargs: {"runtimeMode": "real"},
    )

    async def _raise_retryable_error(*_args, **_kwargs):
        raise RuntimeError("openai_request_failed:RateLimitError")

    monkeypatch.setattr(
        specializer_service,
        "generate_codespace_bundle_artifact",
        _raise_retryable_error,
    )

    async def _load_job(*_args, **_kwargs):
        return SimpleNamespace(
            status="running",
            attempt=specializer_service.CODESPACE_SPECIALIZER_PROVIDER_FALLBACK_ATTEMPT,
            max_attempts=specializer_service.CODESPACE_SPECIALIZER_JOB_MAX_ATTEMPTS,
        )

    monkeypatch.setattr(
        specializer_service,
        "load_idempotent_job",
        _load_job,
    )
    monkeypatch.setattr(
        specializer_service,
        "build_retryable_provider_fallback_bundle_artifact",
        lambda **_kwargs: SimpleNamespace(
            patch_payload_json='{"files":[{"path":"WINOE_TRIAL_CONTEXT.md"}]}',
            base_template_sha=None,
            commit_message="chore: prepare trial baseline",
            model_name="deterministic-provider-fallback",
            model_version="deterministic-provider-fallback",
            prompt_version="v1:codespace",
            test_summary_json={"status": "skipped"},
            provenance_json={"mode": "provider_retryable_fallback"},
        ),
    )

    db = _Db()
    result = await specializer_service.run_codespace_specializer_job(
        db,
        trial_id=31,
        scenario_version_id=24,
    )

    assert result["status"] == "completed_with_retryable_provider_fallback"
    assert result["bundleStatus"] == "ready"
    assert existing_bundle.status == "ready"
    assert existing_bundle.model_name == "deterministic-provider-fallback"
    assert existing_bundle.last_error == ""
    assert db.commits == 1
    assert db.refreshed == [88]
    assert update_calls[0]["status"] == "generating"
    assert update_calls[-1]["status"] == "ready"
