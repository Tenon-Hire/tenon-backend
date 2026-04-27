from __future__ import annotations

import pytest

from app.ai import build_ai_policy_snapshot
from tests.shared.utils.shared_coverage_gaps_utils import *


@pytest.mark.asyncio
async def test_trial_routes_execute_service_calls(monkeypatch):
    user = SimpleNamespace(id=42)
    sim = SimpleNamespace(
        id=1,
        title="Sim",
        role="Backend",
        tech_stack="Python",
        seniority="Mid",
        focus="API",
        company_id=7,
        template_key="python-fastapi",
        scenario_template="default-5day-node-postgres",
        status="ready_for_review",
        generating_at=datetime.now(UTC),
        ready_for_review_at=datetime.now(UTC),
        activated_at=None,
        terminated_at=None,
        created_at=datetime.now(UTC),
        active_scenario_version_id=10,
        pending_scenario_version_id=11,
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
    task = SimpleNamespace(
        id=9,
        day_index=1,
        type="code",
        title="Task",
        description="Task description",
        max_score=5,
    )
    scenario_job = SimpleNamespace(id="job-123")
    active_snapshot = build_ai_policy_snapshot(
        trial=SimpleNamespace(
            ai_notice_version=sim.ai_notice_version,
            ai_notice_text=sim.ai_notice_text,
            ai_eval_enabled_by_day=sim.ai_eval_enabled_by_day,
        )
    )
    pending_snapshot = build_ai_policy_snapshot(
        trial=SimpleNamespace(
            ai_notice_version=sim.ai_notice_version,
            ai_notice_text=sim.ai_notice_text,
            ai_eval_enabled_by_day=sim.ai_eval_enabled_by_day,
        )
    )
    active_version = SimpleNamespace(
        id=10,
        version_index=1,
        status="ready",
        locked_at=None,
        storyline_md="Active storyline",
        task_prompts_json=[],
        rubric_json={},
        focus_notes="Active notes",
        model_name="claude-opus-4.6",
        model_version="2025-10-01",
        prompt_version="prompt-v1",
        rubric_version="rubric-v1",
        ai_policy_snapshot_json=active_snapshot,
    )
    pending_version = SimpleNamespace(
        id=11,
        version_index=2,
        status="ready",
        locked_at=datetime.now(UTC),
        storyline_md="Pending storyline",
        task_prompts_json=[],
        rubric_json={},
        focus_notes="Pending notes",
        model_name="gpt-5.2-codex",
        model_version="2025-10-01",
        prompt_version="prompt-v2",
        rubric_version="rubric-v2",
        ai_policy_snapshot_json=pending_snapshot,
    )
    monkeypatch.setattr(
        sim_create_route, "ensure_talent_partner_or_none", lambda _u: None
    )
    monkeypatch.setattr(
        sim_detail_route, "ensure_talent_partner_or_none", lambda _u: None
    )
    monkeypatch.setattr(
        sim_list_route, "ensure_talent_partner_or_none", lambda _u: None
    )

    async def _create_sim_with_tasks(*_a, **_k):
        return sim, [task], scenario_job

    async def _require_owned(*_a, **_k):
        return sim, [task]

    async def _list_sims(*_a, **_k):
        return [(sim, 2)]

    async def _get_active_scenario(*_a, **_k):
        return active_version

    async def _get_pending_scenario(*_a, **_k):
        return pending_version

    async def _load_latest_job(*_a, **_k):
        return scenario_job

    async def _trial_background_failures(*_a, **_k):
        return SimpleNamespace(
            hasFailedJobs=False,
            failedJobsCount=0,
            latestFailure=None,
        )

    captured_detail = {}

    monkeypatch.setattr(
        sim_create_route.trial_service,
        "create_trial_with_tasks",
        _create_sim_with_tasks,
    )
    monkeypatch.setattr(
        sim_detail_route.trial_service,
        "require_owned_trial_with_tasks",
        _require_owned,
    )
    monkeypatch.setattr(
        sim_detail_route.trial_service,
        "get_active_scenario_version",
        _get_active_scenario,
    )
    monkeypatch.setattr(
        sim_detail_route,
        "_load_scenario_version",
        _get_pending_scenario,
    )
    monkeypatch.setattr(
        sim_detail_route,
        "_load_latest_scenario_generation_job",
        _load_latest_job,
    )
    monkeypatch.setattr(
        sim_detail_route,
        "trial_background_failures",
        _trial_background_failures,
    )
    monkeypatch.setattr(
        sim_detail_route,
        "render_trial_detail",
        lambda _sim, _tasks, _active, **_kwargs: captured_detail.update(_kwargs)
        or {
            "id": _sim.id,
            "title": _sim.title,
            "tasks": _tasks,
        },
    )
    monkeypatch.setattr(sim_list_route.trial_service, "list_trials", _list_sims)

    class _DbStub:
        async def scalar(self, *_args, **_kwargs):
            return None

    db = _DbStub()

    created = await sim_create_route.create_trial(
        payload=SimpleNamespace(),
        db=db,
        user=user,
    )
    rendered_detail = sim_detail_render_route.render_trial_detail(
        sim,
        [task],
        active_version,
        pending_scenario_version=pending_version,
        current_ai_policy_snapshot_json=pending_snapshot,
    )
    detail = await sim_detail_route.get_trial_detail(
        trial_id=sim.id,
        db=db,
        user=user,
    )
    listed = await sim_list_route.list_trials(db=db, user=user)
    assert created.id == sim.id
    assert detail["id"] == sim.id
    assert captured_detail["current_ai_policy_snapshot_json"] is pending_snapshot
    assert captured_detail["scenario_generation_job"] is scenario_job
    assert captured_detail["background_failures"].failedJobsCount == 0
    assert rendered_detail.ai.prompt_pack_version == "winoe-ai-pack-v1"
    assert rendered_detail.scenario.id == pending_version.id
    assert listed[0].numCandidates == 2
