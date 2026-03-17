from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.api.routers import simulations as recruiter_sims
from app.api.routers.simulations_routes import candidates_compare as compare_router


def _request(host: str = "127.0.0.1"):
    return SimpleNamespace(headers={}, client=SimpleNamespace(host=host))


class _FakeDB:
    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None


@pytest.mark.asyncio
async def test_create_candidate_invite_happy_path(monkeypatch):
    user = SimpleNamespace(id=1)
    cs = SimpleNamespace(id=2, token="tok")
    task_day2 = SimpleNamespace(
        id=10, day_index=2, type="code", template_repo="org/template"
    )
    task_day3 = SimpleNamespace(
        id=11, day_index=3, type="debug", template_repo="org/template"
    )

    async def _require_owned_with_tasks(db, simulation_id, recruiter_id):
        assert recruiter_id == user.id
        return (
            SimpleNamespace(
                id=simulation_id,
                title="Sim",
                role="Engineer",
                status="active_inviting",
            ),
            [task_day2, task_day3],
        )

    async def _lock_active_scenario_for_invites(db, simulation_id, now):
        return SimpleNamespace(id=777)

    async def _create_or_resend_invite(
        db, simulation_id, payload, now, scenario_version_id=None
    ):
        assert payload.candidateName == "Name"
        return cs, "created"

    async def _send_invite_email(*_args, **_kwargs):
        return SimpleNamespace(status="sent")

    async def _ensure_workspace(*_args, **_kwargs):
        return SimpleNamespace(id="ws")

    monkeypatch.setattr(recruiter_sims, "ensure_recruiter_or_none", lambda _u: None)
    monkeypatch.setattr(
        recruiter_sims.sim_service,
        "require_owned_simulation_with_tasks",
        _require_owned_with_tasks,
    )
    monkeypatch.setattr(
        recruiter_sims.sim_service,
        "lock_active_scenario_for_invites",
        _lock_active_scenario_for_invites,
    )
    monkeypatch.setattr(
        recruiter_sims.sim_service, "create_or_resend_invite", _create_or_resend_invite
    )
    monkeypatch.setattr(
        recruiter_sims.notification_service, "send_invite_email", _send_invite_email
    )
    monkeypatch.setattr(
        recruiter_sims.submission_service, "ensure_workspace", _ensure_workspace
    )
    monkeypatch.setattr(
        recruiter_sims.sim_service,
        "invite_url",
        lambda token: f"https://portal/{token}",
    )
    email_service = SimpleNamespace(
        send_email=lambda **_k: SimpleNamespace(status="sent")
    )

    payload = SimpleNamespace(candidateName="Name", inviteEmail="a@b.com")
    resp = await recruiter_sims.create_candidate_invite(
        simulation_id=5,
        payload=payload,
        request=_request(),
        db=_FakeDB(),
        user=user,
        email_service=email_service,
        github_client=SimpleNamespace(),
    )
    assert resp.inviteUrl.endswith("/tok")
    assert resp.candidateSessionId == cs.id
    assert resp.outcome == "created"


@pytest.mark.asyncio
async def test_list_simulation_candidates_calls_service(monkeypatch):
    user = SimpleNamespace(id=7)
    cs = SimpleNamespace(
        id=11,
        invite_email="x@y.com",
        candidate_name="Jane",
        status="in_progress",
        started_at=datetime.now(UTC),
        completed_at=None,
    )
    rows = [(cs, None)]

    monkeypatch.setattr(recruiter_sims, "ensure_recruiter_or_none", lambda _u: None)

    async def _require_owned(*_a, **_k):
        return cs

    monkeypatch.setattr(
        recruiter_sims.sim_service,
        "require_owned_simulation",
        _require_owned,
    )

    async def _list_candidates(*_a, **_k):
        return rows

    monkeypatch.setattr(
        recruiter_sims.sim_service, "list_candidates_with_profile", _list_candidates
    )

    resp = await recruiter_sims.list_simulation_candidates(
        simulation_id=9, db=None, user=user
    )
    assert resp[0].candidateSessionId == cs.id
    assert resp[0].hasFitProfile is False


@pytest.mark.asyncio
async def test_list_simulation_candidates_compare_logs_and_returns_payload(monkeypatch):
    user = SimpleNamespace(id=77)
    summary = {
        "simulationId": 9,
        "candidates": [
            {
                "candidateSessionId": 11,
                "candidateName": "Candidate A",
                "candidateDisplayName": "Candidate A",
                "status": "scheduled",
                "fitProfileStatus": "none",
                "overallFitScore": None,
                "recommendation": None,
                "dayCompletion": {
                    "1": False,
                    "2": False,
                    "3": False,
                    "4": False,
                    "5": False,
                },
                "updatedAt": datetime.now(UTC),
            }
        ],
    }

    monkeypatch.setattr(compare_router, "ensure_recruiter", lambda _u: None)

    async def _list_compare(*_args, **_kwargs):
        return summary

    log_events: list[str] = []

    def _capture_log(message, *_args):
        log_events.append(str(message))

    monkeypatch.setattr(
        compare_router.sim_service,
        "list_candidates_compare_summary",
        _list_compare,
    )
    monkeypatch.setattr(compare_router.logger, "info", _capture_log)

    response = await compare_router.list_simulation_candidates_compare(
        simulation_id=9,
        db=SimpleNamespace(),
        user=user,
    )

    assert response.simulationId == 9
    assert response.candidates[0].candidateSessionId == 11
    assert any("Simulation candidates compare fetched" in line for line in log_events)
