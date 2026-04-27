from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.ai import AIPolicySnapshotError, build_ai_policy_snapshot
from app.shared.database.shared_database_models_model import Task, Trial
from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
)
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.trials import services as trial_service
from app.trials.routes.trials_routes import detail as detail_route
from app.trials.routes.trials_routes.trials_routes_trials_routes_trials_routes_detail_render_routes import (
    _generation_failure_summary,
    _generation_status,
    _latest_relevant_scenario_version,
    _scenario_agent_runtime_summary,
    _scenario_review_bundle_status,
    _scenario_snapshot_summary,
)
from tests.shared.factories import create_talent_partner, create_trial


@pytest.mark.asyncio
async def test_get_trial_detail_happy_path(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="owner-detail@example.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    tasks[1].max_score = 42
    await async_session.commit()

    res = await async_client.get(
        f"/api/trials/{sim.id}", headers=auth_header_factory(talent_partner)
    )
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["id"] == sim.id
    assert body["status"] == sim.status
    assert body["generationStatus"] == "ready_for_review"
    assert body["activeScenarioVersionId"] == sim.active_scenario_version_id
    assert body["pendingScenarioVersionId"] is None
    assert body["scenario"]["id"] == sim.active_scenario_version_id
    assert body["scenario"]["versionIndex"] == 1
    assert body["scenario"]["status"] in {"ready", "locked"}
    assert body["scenario"]["lockedAt"] is None
    assert body["scenario"]["notes"] == sim.focus
    assert body["scenario"]["projectBriefMd"]
    assert "codespaceSpecJson" not in body["scenario"]
    assert "templateKey" not in body
    assert "techStack" not in body
    assert isinstance(body["tasks"], list)
    assert [task["dayIndex"] for task in body["tasks"]] == [
        task.day_index for task in tasks
    ]
    assert "dayIndex" in body["tasks"][0]
    assert "day_index" not in body["tasks"][0]
    assert "description" in body["tasks"][0]
    assert "rubric" in body["tasks"][0]
    assert body["tasks"][0]["rubric"] is None

    day2 = next(task for task in body["tasks"] if task["dayIndex"] == 2)
    assert "templateRepoFullName" not in day2 or day2["templateRepoFullName"] is None
    assert day2["maxScore"] == 42
    day1 = next(task for task in body["tasks"] if task["dayIndex"] == 1)
    assert "templateRepoFullName" not in day1
    assert "preProvisioned" not in day1
    assert "maxScore" not in day1


@pytest.mark.asyncio
async def test_trial_context_round_trips_on_create_and_detail(
    async_client, async_session, auth_header_factory
):
    talent_partner = await create_talent_partner(
        async_session, email="context-detail@example.com"
    )
    payload = {
        "title": "Frontend Trial",
        "role": "Frontend Engineer",
        "preferredLanguageFramework": "react-nextjs",
        "seniority": "mid",
        "focus": "Emphasize documentation and test discipline.",
        "companyContext": {"domain": "social", "productArea": "creator tools"},
        "ai": {
            "noticeVersion": "mvp1",
            "noticeText": "AI may assist with scenario generation.",
            "evalEnabledByDay": {
                "1": True,
                "2": True,
                "3": True,
                "4": False,
                "5": True,
            },
        },
    }

    create_res = await async_client.post(
        "/api/trials",
        json=payload,
        headers=auth_header_factory(talent_partner),
    )
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()
    assert created["seniority"] == "mid"
    assert created["focus"] == payload["focus"]
    assert created["companyContext"] == {
        **payload["companyContext"],
        "preferredLanguageFramework": "react-nextjs",
    }
    assert created["ai"] == payload["ai"]

    trial = await async_session.get(Trial, created["id"])
    assert trial is not None
    tasks = (
        await async_session.scalars(
            select(Task).where(Task.trial_id == trial.id).order_by(Task.day_index)
        )
    ).all()
    assert len(tasks) == 5
    scenario_version = await trial_service.create_initial_scenario_version(
        async_session,
        trial=trial,
        tasks=list(tasks),
    )
    assert scenario_version.ai_policy_snapshot_json == build_ai_policy_snapshot(
        trial=SimpleNamespace(
            ai_notice_version=payload["ai"]["noticeVersion"],
            ai_notice_text=payload["ai"]["noticeText"],
            ai_eval_enabled_by_day=payload["ai"]["evalEnabledByDay"],
        )
    )

    detail_res = await async_client.get(
        f"/api/trials/{created['id']}",
        headers=auth_header_factory(talent_partner),
    )
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()
    assert detail["seniority"] == "mid"
    assert detail["focus"] == payload["focus"]
    assert detail["companyContext"] == {
        **payload["companyContext"],
        "preferredLanguageFramework": "react-nextjs",
    }
    assert detail["ai"]["noticeVersion"] == payload["ai"]["noticeVersion"]
    assert detail["ai"]["noticeText"] == payload["ai"]["noticeText"]
    assert detail["ai"]["evalEnabledByDay"] == payload["ai"]["evalEnabledByDay"]
    assert detail["ai"]["promptPackVersion"] == "winoe-ai-pack-v1"
    assert detail["ai"]["changesPendingRegeneration"] is False


@pytest.mark.asyncio
async def test_get_trial_detail_maps_snapshot_validation_error(monkeypatch):
    monkeypatch.setattr(detail_route, "ensure_talent_partner_or_none", lambda _u: None)

    sim = SimpleNamespace(id=1, company_id=7)
    task = SimpleNamespace(id=9, day_index=1, type="code", title="Task")

    async def _require_owned(*_a, **_k):
        return sim, [task]

    async def _get_active_scenario(*_a, **_k):
        return SimpleNamespace(id=10, status="ready", locked_at=None)

    async def _load_pending(*_a, **_k):
        return None

    async def _load_job(*_a, **_k):
        return None

    async def _trial_background_failures(*_a, **_k):
        return None

    def _render_trial_detail(*_a, **_k):
        raise AIPolicySnapshotError("boom")

    monkeypatch.setattr(
        detail_route.trial_service,
        "require_owned_trial_with_tasks",
        _require_owned,
    )
    monkeypatch.setattr(
        detail_route.trial_service,
        "get_active_scenario_version",
        _get_active_scenario,
    )
    monkeypatch.setattr(detail_route, "_load_scenario_version", _load_pending)
    monkeypatch.setattr(detail_route, "_load_latest_scenario_generation_job", _load_job)
    monkeypatch.setattr(
        detail_route, "trial_background_failures", _trial_background_failures
    )
    monkeypatch.setattr(detail_route, "render_trial_detail", _render_trial_detail)

    with pytest.raises(ApiError) as excinfo:
        await detail_route.get_trial_detail(trial_id=sim.id, db=object(), user=sim)
    assert excinfo.value.status_code == 409
    assert excinfo.value.error_code == "scenario_version_ai_policy_snapshot_invalid"


def test_latest_relevant_scenario_version_prefers_reviewable_pending_only():
    active = SimpleNamespace(id=1, status="ready", locked_at=None)
    pending_generating = SimpleNamespace(id=2, status="generating", locked_at=None)
    pending_ready = SimpleNamespace(id=3, status="ready", locked_at=None)

    assert (
        _latest_relevant_scenario_version(
            active_scenario_version=active,
            pending_scenario_version=pending_generating,
        )
        is active
    )
    assert (
        _latest_relevant_scenario_version(
            active_scenario_version=active,
            pending_scenario_version=pending_ready,
        )
        is pending_ready
    )


def test_generation_failure_summary_accepts_terminal_failed_states():
    for status in ("failed", "dead_letter"):
        summary = _generation_failure_summary(
            SimpleNamespace(id="job-1", status=status, last_error="boom")
        )
        assert summary is not None
        assert summary.jobId == "job-1"
        assert summary.status == "failed"
        assert summary.error == "boom"
        assert summary.retryable is True
        assert summary.canRetry is True


def test_generation_failure_summary_returns_none_for_missing_or_non_terminal_jobs():
    assert _generation_failure_summary(None) is None
    assert (
        _generation_failure_summary(
            SimpleNamespace(id="job-2", status="queued", last_error="boom")
        )
        is None
    )


def test_detail_helpers_handle_non_reviewable_and_non_mapping_state():
    assert _scenario_agent_runtime_summary(None) is None
    snapshot = build_ai_policy_snapshot(
        trial=SimpleNamespace(
            ai_notice_version="mvp1",
            ai_notice_text="AI assistance may be used for evaluation support.",
            ai_eval_enabled_by_day={
                "1": True,
                "2": True,
                "3": True,
                "4": True,
                "5": True,
            },
        )
    )
    snapshot["agents"] = ["bad"]
    with pytest.raises(AIPolicySnapshotError, match="agents_missing"):
        _scenario_agent_runtime_summary(snapshot)

    snapshot = build_ai_policy_snapshot(
        trial=SimpleNamespace(
            ai_notice_version="mvp1",
            ai_notice_text="AI assistance may be used for evaluation support.",
            ai_eval_enabled_by_day={
                "1": True,
                "2": True,
                "3": True,
                "4": True,
                "5": True,
            },
        )
    )
    version = SimpleNamespace(id="sv-1", ai_policy_snapshot_json=snapshot)
    summary = _scenario_snapshot_summary(version, bundle_status="ready")
    assert summary is not None
    assert summary["scenarioVersionId"] == "sv-1"
    assert summary["promptPackVersion"] == "winoe-ai-pack-v1"
    assert summary["bundleStatus"] == "ready"
    assert [agent["key"] for agent in summary["agents"]] == [
        "codeImplementationReviewer",
        "demoPresentationReviewer",
        "designDocReviewer",
        "prestart",
        "reflectionEssayReviewer",
        "winoeReport",
    ]
    assert summary["agents"][0]["provider"] is not None
    assert summary["agents"][0]["model"] is not None
    assert summary["agents"][-1]["promptVersion"] is not None
    assert summary["agents"][-1]["rubricVersion"] is not None

    assert _scenario_snapshot_summary(None, bundle_status=None) is None
    assert (
        _scenario_snapshot_summary(
            SimpleNamespace(id="sv-2", ai_policy_snapshot_json=[]),
            bundle_status=None,
        )
        is None
    )


def test_detail_helpers_cover_bundle_and_generation_status_branches():
    assert (
        _scenario_review_bundle_status(
            active_scenario_version=None,
            pending_scenario_version=None,
            active_bundle_status="active",
            pending_bundle_status="pending",
        )
        is None
    )
    assert (
        _scenario_review_bundle_status(
            active_scenario_version=SimpleNamespace(id="a"),
            pending_scenario_version=None,
            active_bundle_status="active",
            pending_bundle_status="pending",
        )
        == "active"
    )
    assert (
        _scenario_review_bundle_status(
            active_scenario_version=SimpleNamespace(id="a"),
            pending_scenario_version=SimpleNamespace(id="p"),
            active_bundle_status="active",
            pending_bundle_status="pending",
        )
        == "pending"
    )

    assert (
        _generation_status(
            active_scenario_version=None,
            pending_scenario_version=None,
            scenario_generation_job=SimpleNamespace(status="failed"),
            generation_failure=SimpleNamespace(),
        )
        == "failed"
    )
    assert (
        _generation_status(
            active_scenario_version=SimpleNamespace(status="generating"),
            pending_scenario_version=None,
            scenario_generation_job=None,
            generation_failure=None,
        )
        == "generating"
    )
    assert (
        _generation_status(
            active_scenario_version=None,
            pending_scenario_version=SimpleNamespace(status="generating"),
            scenario_generation_job=None,
            generation_failure=None,
        )
        == "generating"
    )
    assert (
        _generation_status(
            active_scenario_version=None,
            pending_scenario_version=None,
            scenario_generation_job=SimpleNamespace(status=JOB_STATUS_QUEUED),
            generation_failure=None,
        )
        == "generating"
    )
    assert (
        _generation_status(
            active_scenario_version=None,
            pending_scenario_version=None,
            scenario_generation_job=SimpleNamespace(status=JOB_STATUS_RUNNING),
            generation_failure=None,
        )
        == "generating"
    )
    assert (
        _generation_status(
            active_scenario_version=SimpleNamespace(status="ready"),
            pending_scenario_version=None,
            scenario_generation_job=None,
            generation_failure=None,
        )
        == "ready_for_review"
    )
    assert (
        _generation_status(
            active_scenario_version=None,
            pending_scenario_version=SimpleNamespace(status="locked"),
            scenario_generation_job=None,
            generation_failure=None,
        )
        == "ready_for_review"
    )
    assert (
        _generation_status(
            active_scenario_version=None,
            pending_scenario_version=None,
            scenario_generation_job=None,
            generation_failure=None,
        )
        == "not_started"
    )
