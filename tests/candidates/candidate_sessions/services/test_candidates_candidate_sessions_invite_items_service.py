from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.candidates.candidate_sessions.services import (
    candidates_candidate_sessions_services_candidates_candidate_sessions_invite_items_service as invite_items_service,
)


@pytest.mark.asyncio
async def test_build_invite_item_uses_progress_snapshot_when_completed_ids_missing(
    monkeypatch,
):
    now = datetime(2026, 3, 26, 12, 0, tzinfo=UTC)
    candidate_session = SimpleNamespace(
        id=7,
        trial_id=19,
        trial=SimpleNamespace(
            id=19,
            title="Trial",
            role="Engineer",
            company=SimpleNamespace(name="Acme"),
        ),
        expires_at=None,
        completed_at=None,
        started_at=None,
        created_at=now,
        token="invite-token",
        status="in_progress",
    )

    async def _tasks_loader(_trial_id: int):
        return [SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=3)]

    async def _progress_snapshot(_db, _candidate_session, *, tasks):
        assert len(tasks) == 3
        return None, {1, 2}, None, 2, 3, False

    monkeypatch.setattr(invite_items_service, "progress_snapshot", _progress_snapshot)
    monkeypatch.setattr(
        invite_items_service,
        "schedule_payload_for_candidate_session",
        lambda _candidate_session, now_utc: {
            "scheduledStartAt": now_utc,
            "candidateTimezone": "UTC",
            "dayWindows": [],
            "scheduleLockedAt": None,
            "currentDayWindow": None,
        },
    )

    item = await invite_items_service.build_invite_item(
        db=object(),
        candidate_session=candidate_session,
        now=now,
        last_submitted_map={},
        tasks_loader=_tasks_loader,
        completed_ids=None,
    )

    assert item.candidateSessionId == 7
    assert item.trialId == 19
    assert item.progress.completed == 2
    assert item.progress.total == 3
    assert item.companyName == "Acme"
