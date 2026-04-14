from types import SimpleNamespace

import pytest

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import (
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
)
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
    assert body["templateKey"] == sim.template_key
    assert body["techStack"] == sim.tech_stack
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
    assert "templateRepoFullName" in day2
    assert day2["templateRepoFullName"]
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
        "techStack": "react-nextjs",
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
    assert created["companyContext"] == payload["companyContext"]
    assert created["ai"] == payload["ai"]

    detail_res = await async_client.get(
        f"/api/trials/{created['id']}",
        headers=auth_header_factory(talent_partner),
    )
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()
    assert detail["seniority"] == "mid"
    assert detail["focus"] == payload["focus"]
    assert detail["companyContext"] == payload["companyContext"]
    assert detail["ai"]["noticeVersion"] == payload["ai"]["noticeVersion"]
    assert detail["ai"]["noticeText"] == payload["ai"]["noticeText"]
    assert detail["ai"]["evalEnabledByDay"] == payload["ai"]["evalEnabledByDay"]
    assert detail["ai"]["promptPackVersion"] == "winoe-ai-pack-v1"
    assert detail["ai"]["changesPendingRegeneration"] is False


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
    assert _scenario_agent_runtime_summary({"agents": ["bad"]}) is None

    snapshot = {
        "promptPackVersion": "pack-v2",
        "agents": {
            "prestart": {
                "runtime": {
                    "runtimeMode": "primary",
                    "provider": "anthropic",
                    "model": "claude-opus-4.6",
                },
                "promptVersion": "v9",
                "rubricVersion": "r9",
            },
            "ignore-me": "not-a-mapping",
        },
    }
    version = SimpleNamespace(id="sv-1", ai_policy_snapshot_json=snapshot)
    summary = _scenario_snapshot_summary(version, bundle_status="ready")
    assert summary is not None
    assert summary["scenarioVersionId"] == "sv-1"
    assert summary["promptPackVersion"] == "pack-v2"
    assert summary["bundleStatus"] == "ready"
    assert summary["agents"] == [
        {
            "key": "prestart",
            "provider": "anthropic",
            "model": "claude-opus-4.6",
            "runtimeMode": "primary",
            "promptVersion": "v9",
            "rubricVersion": "r9",
        }
    ]

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
