from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.ai import (
    compute_ai_policy_snapshot_digest,
    validate_ai_policy_snapshot_contract,
)
from app.evaluations.repositories import (
    RUBRIC_SNAPSHOT_SCOPE_WINOE,
)
from app.evaluations.services import (
    evaluations_services_evaluations_winoe_report_pipeline_runner_service as runner_service,
)
from app.evaluations.services import (
    evaluations_services_evaluations_winoe_rubric_snapshots_service as rubric_service,
)
from app.evaluations.services.evaluations_services_evaluations_evaluator_models_service import (
    EvaluationInputBundle,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_report_access_service import (
    get_candidate_session_evaluation_context,
    has_company_access,
)
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    ScenarioVersion,
)
from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import (
    _session_maker_for,
)
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_process_evaluation_run_job_uses_persisted_rubric_snapshots(
    monkeypatch, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="pipeline-rubric@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(async_session, trial=trial)
    scenario_version = await async_session.scalar(
        select(ScenarioVersion).where(
            ScenarioVersion.id == candidate_session.scenario_version_id
        )
    )
    assert scenario_version is not None

    materialized = await rubric_service.materialize_scenario_version_rubric_snapshots(
        async_session, scenario_version=scenario_version, trial=trial
    )
    baseline_snapshot = next(
        snapshot
        for snapshot in materialized["snapshots"]
        if snapshot.scope == RUBRIC_SNAPSHOT_SCOPE_WINOE
        and snapshot.rubric_key == "designDocReviewer"
    )

    monkeypatch.setattr(
        rubric_service,
        "_read_text_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("pipeline should not reread rubric source files")
        ),
    )

    captured: dict[str, object] = {}

    async def fake_get_or_start_run(**_kwargs):
        return (
            SimpleNamespace(
                id=9001,
                basis_fingerprint="basis-9001",
                model_version="2026-03-12",
                prompt_version="winoe-report-v1",
                rubric_version="rubric-v1",
            ),
            None,
        )

    async def fake_evaluate_and_finalize_run(**kwargs):
        captured["bundle"] = kwargs["bundle"]
        captured["run_metadata"] = kwargs["run_metadata"]
        return SimpleNamespace(
            id=9001,
            basis_fingerprint="basis-9001",
            model_version=kwargs["bundle"].model_version,
            prompt_version=kwargs["bundle"].prompt_version,
            rubric_version=kwargs["bundle"].rubric_version,
        )

    monkeypatch.setattr(runner_service, "_get_or_start_run", fake_get_or_start_run)
    monkeypatch.setattr(
        runner_service, "_evaluate_and_finalize_run", fake_evaluate_and_finalize_run
    )
    evaluator_service = SimpleNamespace(
        EvaluationInputBundle=EvaluationInputBundle,
        get_winoe_report_evaluator=lambda: object(),
    )

    deps = dict(
        async_session_maker=_session_maker_for(async_session),
        get_candidate_session_evaluation_context=get_candidate_session_evaluation_context,
        has_company_access=has_company_access,
        _tasks_by_day=AsyncMock(return_value={}),
        _submissions_by_day=AsyncMock(return_value={}),
        _day_audits_by_day=AsyncMock(return_value={}),
        _resolve_day4_transcript=AsyncMock(return_value=(None, "transcript:missing")),
        evaluation_repo=SimpleNamespace(),
        evaluation_runs=SimpleNamespace(),
        winoe_report_repository=SimpleNamespace(),
        evaluator_service=evaluator_service,
        logger=SimpleNamespace(
            info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None
        ),
    )
    result = await runner_service.process_evaluation_run_job_impl(
        {
            "candidateSessionId": candidate_session.id,
            "companyId": trial.company_id,
            "requestedByUserId": talent_partner.id,
            "basisFingerprint": "ignored",
        },
        **deps,
    )

    assert result["status"] == "completed"
    bundle = captured["bundle"]
    assert bundle is not None
    assert (
        bundle.ai_policy_snapshot_json["agents"]["designDocReviewer"][
            "resolvedRubricMd"
        ]
        == baseline_snapshot.content_md
    )
    assert bundle.ai_policy_snapshot_json[
        "snapshotDigest"
    ] == compute_ai_policy_snapshot_digest(bundle.ai_policy_snapshot_json)
    validate_ai_policy_snapshot_contract(
        bundle.ai_policy_snapshot_json,
        scenario_version_id=candidate_session.scenario_version_id,
    )
    assert bundle.ai_policy_snapshot_json["rubricSnapshots"]
    assert {
        item["snapshotId"] for item in bundle.ai_policy_snapshot_json["rubricSnapshots"]
    } == {item["snapshotId"] for item in materialized["rubricSnapshots"]}
    assert {
        item["snapshotId"] for item in captured["run_metadata"]["rubricSnapshots"]
    } == {item["snapshotId"] for item in materialized["rubricSnapshots"]}


@pytest.mark.asyncio
async def test_process_evaluation_run_job_reuses_same_snapshot_ids_for_same_trial(
    monkeypatch, async_session
):
    talent_partner = await create_talent_partner(
        async_session, email="pipeline-same-trial@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_a = await create_candidate_session(async_session, trial=trial)
    candidate_b = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="pipeline-same-trial-b@example.com",
    )
    scenario_version = await async_session.scalar(
        select(ScenarioVersion).where(
            ScenarioVersion.id == candidate_a.scenario_version_id
        )
    )
    assert scenario_version is not None
    materialized = await rubric_service.materialize_scenario_version_rubric_snapshots(
        async_session, scenario_version=scenario_version, trial=trial
    )
    expected_ids = {item["snapshotId"] for item in materialized["rubricSnapshots"]}

    monkeypatch.setattr(
        rubric_service,
        "_read_text_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("pipeline should not reread rubric source files")
        ),
    )

    seen_snapshot_id_sets: list[set[int]] = []

    async def fake_get_or_start_run(**_kwargs):
        return (
            SimpleNamespace(
                id=9101,
                basis_fingerprint="basis-9101",
                model_version="2026-03-12",
                prompt_version="winoe-report-v1",
                rubric_version="rubric-v1",
            ),
            None,
        )

    async def fake_evaluate_and_finalize_run(**kwargs):
        seen_snapshot_id_sets.append(
            {
                int(item["snapshotId"])
                for item in kwargs["bundle"].ai_policy_snapshot_json["rubricSnapshots"]
            }
        )
        return SimpleNamespace(
            id=9101,
            basis_fingerprint="basis-9101",
            model_version=kwargs["bundle"].model_version,
            prompt_version=kwargs["bundle"].prompt_version,
            rubric_version=kwargs["bundle"].rubric_version,
        )

    monkeypatch.setattr(runner_service, "_get_or_start_run", fake_get_or_start_run)
    monkeypatch.setattr(
        runner_service, "_evaluate_and_finalize_run", fake_evaluate_and_finalize_run
    )
    evaluator_service = SimpleNamespace(
        EvaluationInputBundle=EvaluationInputBundle,
        get_winoe_report_evaluator=lambda: object(),
    )

    deps = dict(
        async_session_maker=_session_maker_for(async_session),
        get_candidate_session_evaluation_context=get_candidate_session_evaluation_context,
        has_company_access=has_company_access,
        _tasks_by_day=AsyncMock(return_value={}),
        _submissions_by_day=AsyncMock(return_value={}),
        _day_audits_by_day=AsyncMock(return_value={}),
        _resolve_day4_transcript=AsyncMock(return_value=(None, "transcript:missing")),
        evaluation_repo=SimpleNamespace(),
        evaluation_runs=SimpleNamespace(),
        winoe_report_repository=SimpleNamespace(),
        evaluator_service=evaluator_service,
        logger=SimpleNamespace(
            info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None
        ),
    )
    for candidate_session in (candidate_a, candidate_b):
        result = await runner_service.process_evaluation_run_job_impl(
            {
                "candidateSessionId": candidate_session.id,
                "companyId": trial.company_id,
                "requestedByUserId": talent_partner.id,
            },
            **deps,
        )
        assert result["status"] == "completed"

    assert seen_snapshot_id_sets
    assert all(snapshot_ids == expected_ids for snapshot_ids in seen_snapshot_id_sets)
