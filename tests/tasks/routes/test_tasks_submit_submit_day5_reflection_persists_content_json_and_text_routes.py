from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_submit_api_utils import *


@pytest.mark.asyncio
async def test_submit_day5_reflection_persists_content_json_and_text(
    async_client, async_session: AsyncSession
):
    talent_partner = await create_talent_partner(
        async_session, email="day5-valid@test.com"
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

    payload = build_day5_reflection_payload()
    response = await async_client.post(
        f"/api/tasks/{tasks[4].id}/submit",
        headers=candidate_headers(cs.id, f"candidate:{cs.invite_email}"),
        json=payload,
    )
    assert response.status_code == 201, response.text

    submission = await async_session.get(Submission, response.json()["submissionId"])
    assert submission is not None
    assert submission.content_text == payload["contentText"]
    assert submission.content_json == {
        "kind": "day5_reflection",
        "markdown": payload["contentText"],
        "sections": payload["reflection"],
    }
