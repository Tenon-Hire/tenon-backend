import pytest

from tests.shared.factories import (
    create_candidate_session,
    create_submission,
    create_talent_partner,
    create_trial,
)


@pytest.mark.asyncio
async def test_submissions_list_forbidden_for_non_talent_partner(
    async_client, async_session
):
    user = await create_talent_partner(
        async_session,
        email="nontalent_partner@sim.com",
        name="NR",
        company_name="NR Co",
    )
    user.role = "candidate"
    await async_session.commit()

    res = await async_client.get(
        "/api/submissions", headers={"x-dev-user-email": user.email}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_submissions_detail_403_when_wrong_company(async_client, async_session):
    owner = await create_talent_partner(async_session, email="owner@sim.com")
    other = await create_talent_partner(async_session, email="other@sim.com")
    sim, tasks = await create_trial(async_session, created_by=owner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")
    sub = await create_submission(
        async_session,
        candidate_session=cs,
        task=tasks[0],
        content_text="answer",
    )

    res = await async_client.get(
        f"/api/submissions/{sub.id}",
        headers={"x-dev-user-email": other.email},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_submissions_list_includes_workflow_fields_without_missing_greenlet(
    async_client, async_session
):
    owner = await create_talent_partner(async_session, email="owner-list@sim.com")
    sim, tasks = await create_trial(async_session, created_by=owner)
    cs = await create_candidate_session(async_session, trial=sim, status="in_progress")
    handoff_task = next(task for task in tasks if task.type == "handoff")
    await create_submission(
        async_session,
        candidate_session=cs,
        task=handoff_task,
        content_text="handoff submission",
        workflow_run_id="987654",
        workflow_run_status="COMPLETED",
        workflow_run_conclusion="SUCCESS",
    )
    await async_session.commit()

    res = await async_client.get(
        f"/api/submissions?candidateSessionId={cs.id}",
        headers={"x-dev-user-email": owner.email},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["submissionId"] > 0
    assert body["items"][0]["taskId"] == handoff_task.id
    assert body["items"][0]["candidateSessionId"] == cs.id
    assert body["items"][0]["testResults"]["runStatus"] == "completed"
    assert body["items"][0]["testResults"]["conclusion"] == "success"
