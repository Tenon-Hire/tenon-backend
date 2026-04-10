from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.talent_partners.services import (
    talent_partners_services_talent_partners_admin_ops_service as admin_ops_service,
)


@pytest.mark.asyncio
async def test_admin_day_window_control_route_maps_response(async_client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setattr(
        admin_ops_service,
        "set_candidate_session_day_window",
        AsyncMock(
            return_value=admin_ops_service.CandidateSessionDayWindowControlResult(
                candidate_session_id=42,
                candidate_status="in_progress",
                status="ok",
                target_day_index=4,
                candidate_timezone="America/New_York",
                scheduled_start_at=datetime(2026, 4, 1, 13, 0, tzinfo=UTC),
                schedule_locked_at=datetime(2026, 4, 3, 13, 0, tzinfo=UTC),
                day_windows=[
                    {
                        "dayIndex": 1,
                        "windowStartAt": datetime(2026, 4, 1, 13, 0, tzinfo=UTC),
                        "windowEndAt": datetime(2026, 4, 1, 14, 0, tzinfo=UTC),
                    }
                ],
                current_day_window={
                    "dayIndex": 4,
                    "windowStartAt": datetime(2026, 4, 4, 13, 0, tzinfo=UTC),
                    "windowEndAt": datetime(2026, 4, 4, 14, 0, tzinfo=UTC),
                    "state": "active",
                },
                audit_id="audit-day-window",
            )
        ),
    )

    response = await async_client.post(
        "/api/admin/candidate_sessions/42/day_windows/control",
        headers={"X-Admin-Key": "test-admin-key"},
        json={
            "targetDayIndex": 4,
            "reason": "accelerate day 4",
            "candidateTimezone": "America/New_York",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidateSessionId"] == 42
    assert payload["candidateStatus"] == "in_progress"
    assert payload["targetDayIndex"] == 4
    assert payload["auditId"] == "audit-day-window"
    assert payload["currentDayWindow"]["state"] == "active"


@pytest.mark.asyncio
async def test_admin_day_window_control_route_requires_admin_key(
    async_client, monkeypatch
):
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-admin-key")
    response = await async_client.post(
        "/api/admin/candidate_sessions/42/day_windows/control",
        json={"targetDayIndex": 4, "reason": "accelerate day 4"},
    )
    assert response.status_code == 404
