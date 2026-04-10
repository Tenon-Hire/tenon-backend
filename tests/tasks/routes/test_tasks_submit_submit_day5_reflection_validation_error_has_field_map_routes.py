from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_submit_day5_reflection_validation_error_has_field_map(
    async_client, async_session: AsyncSession
):
    talent_partner = await create_talent_partner(
        async_session, email="day5-invalid@test.com"
    )
    sim, tasks = await create_trial_factory(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    for task in tasks[:4]:
        await create_submission(
            async_session,
            candidate_session=cs,
            task=task,
            content_text=f"day{task.day_index}",
        )
    await async_session.commit()

    response = await async_client.post(
        f"/api/tasks/{tasks[4].id}/submit",
        headers=candidate_headers(cs.id, f"candidate:{cs.invite_email}"),
        json={
            "reflection": {
                "challenges": "short",
                "decisions": " ",
                "tradeoffs": (
                    "This section has enough text to pass the per-section minimum."
                ),
                "communication": (
                    "This section also has enough text to satisfy validation."
                ),
            },
            "contentText": "## Reflection",
        },
    )

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["errorCode"] == "VALIDATION_ERROR"
    fields = body["details"]["fields"]
    assert fields["reflection.challenges"] == ["too_short"]
    assert fields["reflection.decisions"] == ["missing"]
    assert fields["reflection.next"] == ["missing"]
