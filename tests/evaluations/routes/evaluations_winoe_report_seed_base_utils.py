from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from tests.shared.factories import (
    create_candidate_session,
    create_submission,
    create_talent_partner,
    create_trial,
)


async def _seed_winoe_report_candidate_session(
    async_session: AsyncSession,
    *,
    ai_eval_enabled_by_day: dict[str, bool] | None = None,
):
    talent_partner = await create_talent_partner(
        async_session,
        email="winoe-report-owner@test.com",
    )
    trial, tasks = await create_trial(
        async_session,
        created_by=talent_partner,
        ai_eval_enabled_by_day=ai_eval_enabled_by_day,
    )
    candidate_session = await create_candidate_session(
        async_session,
        trial=trial,
        status="completed",
        candidate_name="Winoe Report Candidate",
        invite_email="winoe-report-candidate@example.com",
    )
    tasks_by_day = {task.day_index: task for task in tasks}
    return talent_partner, candidate_session, tasks_by_day


async def _seed_day1_day2_day3_submissions(
    async_session: AsyncSession,
    *,
    candidate_session,
    tasks_by_day,
) -> None:
    await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks_by_day[1],
        content_text="System design plan with tradeoffs, constraints, and rollout notes.",
        content_json={"kind": "day1_design", "sections": {"overview": "plan"}},
    )
    day2_submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks_by_day[2],
        content_text=None,
        code_repo_path="acme/winoe-report-repo",
        commit_sha="mutable-day2-sha",
        workflow_run_id="2002",
        diff_summary_json=json.dumps({"base": "base-day2", "head": "head-day2"}),
        tests_passed=5,
        tests_failed=1,
        test_output=json.dumps({"passed": 5, "failed": 1, "total": 6}),
    )
    day2_submission.checkpoint_sha = "mutable-day2-checkpoint"
    day3_submission = await create_submission(
        async_session,
        candidate_session=candidate_session,
        task=tasks_by_day[3],
        content_text=None,
        code_repo_path="acme/winoe-report-repo",
        commit_sha="mutable-day3-sha",
        workflow_run_id="3003",
        diff_summary_json=json.dumps({"base": "base-day3", "head": "head-day3"}),
        tests_passed=6,
        tests_failed=0,
        test_output=json.dumps({"passed": 6, "failed": 0, "total": 6}),
    )
    day3_submission.final_sha = "mutable-day3-final"
