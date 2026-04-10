from __future__ import annotations

import pytest

from tests.tasks.routes.test_tasks_run_api_utils import *


@pytest.mark.asyncio
async def test_get_run_result_throttled_when_polling_too_fast(
    async_client, async_session, candidate_header_factory, actions_stubber, monkeypatch
):
    monkeypatch.setattr(candidate_submissions.settings, "ENV", "prod")
    candidate_submissions.rate_limit.limiter.reset()
    original_rule = dict(candidate_submissions._RATE_LIMIT_RULE)
    candidate_submissions._RATE_LIMIT_RULE[
        "poll"
    ] = candidate_submissions.rate_limit.RateLimitRule(limit=5, window_seconds=60.0)

    actions_stubber()
    talent_partner = await create_talent_partner(
        async_session, email="poll-throttle@sim.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    cs = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
        with_default_schedule=True,
    )
    await create_submission(
        async_session, candidate_session=cs, task=tasks[0], content_text="day1"
    )
    await async_session.commit()

    headers = candidate_header_factory(cs)
    await async_client.post(
        f"/api/tasks/{tasks[1].id}/codespace/init",
        headers=headers,
        json={"githubUsername": "octocat"},
    )

    first = await async_client.get(
        f"/api/tasks/{tasks[1].id}/run/123",
        headers=headers,
    )
    assert first.status_code == 200, first.text

    second = await async_client.get(
        f"/api/tasks/{tasks[1].id}/run/123",
        headers=headers,
    )
    assert second.status_code == 429

    monkeypatch.setattr(candidate_submissions.settings, "ENV", "local")
    candidate_submissions._RATE_LIMIT_RULE.update(original_rule)
    candidate_submissions.rate_limit.limiter.reset()
