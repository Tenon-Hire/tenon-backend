from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains import (
    CandidateSession,
    Company,
    Job,
    ScenarioVersion,
    Simulation,
    Submission,
    Task,
    User,
)
from app.domains.simulations.ai_config import (
    AI_NOTICE_DEFAULT_TEXT,
    AI_NOTICE_DEFAULT_VERSION,
    default_ai_eval_enabled_by_day,
)
from app.domains.simulations.blueprints import DEFAULT_5_DAY_BLUEPRINT
from app.services.scheduling.day_windows import serialize_day_windows
from app.services.tasks.template_catalog import (
    DEFAULT_TEMPLATE_KEY,
    resolve_template_repo_full_name,
)


async def create_company(session: AsyncSession, *, name: str = "Acme Corp") -> Company:
    company = Company(name=name)
    session.add(company)
    await session.flush()
    return company


async def create_recruiter(
    session: AsyncSession,
    *,
    email: str = "recruiter@example.com",
    company: Company | None = None,
    company_name: str | None = None,
    name: str | None = None,
) -> User:
    company = company or await create_company(
        session, name=company_name or f"{email}-co"
    )
    user = User(
        name=name or email.split("@")[0],
        email=email,
        role="recruiter",
        company_id=company.id,
        password_hash="",
    )
    session.add(user)
    await session.flush()
    return user


async def create_simulation(
    session: AsyncSession,
    *,
    created_by: User,
    title: str = "Backend Simulation",
    role: str = "Backend Engineer",
    tech_stack: str = "Node.js, PostgreSQL",
    seniority: str = "Mid",
    focus: str = "Deliver a backend feature over 5 days",
    template_key: str = DEFAULT_TEMPLATE_KEY,
    company_context: dict[str, str] | None = None,
    ai_notice_version: str | None = None,
    ai_notice_text: str | None = None,
    ai_eval_enabled_by_day: dict[str, bool] | None = None,
) -> tuple[Simulation, list[Task]]:
    if ai_notice_version is None:
        ai_notice_version = AI_NOTICE_DEFAULT_VERSION
    if ai_notice_text is None:
        ai_notice_text = AI_NOTICE_DEFAULT_TEXT
    if ai_eval_enabled_by_day is None:
        ai_eval_enabled_by_day = default_ai_eval_enabled_by_day()

    sim = Simulation(
        company_id=created_by.company_id,
        title=title,
        role=role,
        tech_stack=tech_stack,
        seniority=seniority,
        focus=focus,
        scenario_template="default-5day-node-postgres",
        created_by=created_by.id,
        status="generating",
        generating_at=datetime.now(UTC),
        template_key=template_key,
        company_context=company_context,
        ai_notice_version=ai_notice_version,
        ai_notice_text=ai_notice_text,
        ai_eval_enabled_by_day=ai_eval_enabled_by_day,
    )
    session.add(sim)
    await session.flush()

    tasks: list[Task] = []
    for blueprint_task in DEFAULT_5_DAY_BLUEPRINT:
        template_repo = None
        if blueprint_task["type"] in {"code", "debug"}:
            template_repo = resolve_template_repo_full_name(template_key)
        task = Task(
            simulation_id=sim.id,
            day_index=blueprint_task["day_index"],
            type=blueprint_task["type"],
            title=blueprint_task["title"],
            description=blueprint_task["description"],
            template_repo=template_repo,
        )
        session.add(task)
        tasks.append(task)

    await session.flush()
    scenario_version = ScenarioVersion(
        simulation_id=sim.id,
        version_index=1,
        status="ready",
        storyline_md=f"# {sim.title}",
        task_prompts_json=[
            {
                "dayIndex": task.day_index,
                "type": task.type,
                "title": task.title,
                "description": task.description,
            }
            for task in sorted(tasks, key=lambda item: item.day_index)
        ],
        rubric_json={},
        focus_notes=sim.focus or "",
        template_key=sim.template_key,
        tech_stack=sim.tech_stack,
        seniority=sim.seniority,
    )
    session.add(scenario_version)
    await session.flush()
    sim.active_scenario_version_id = scenario_version.id
    sim.status = "active_inviting"
    sim.activated_at = datetime.now(UTC)
    await session.flush()
    tasks.sort(key=lambda t: t.day_index)
    return sim, tasks


async def create_candidate_session(
    session: AsyncSession,
    *,
    simulation: Simulation,
    candidate_name: str = "Jane Candidate",
    invite_email: str = "jane@example.com",
    status: str = "not_started",
    token: str | None = None,
    expires_in_days: int = 14,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    candidate_email: str | None = None,
    candidate_auth0_sub: str | None = None,
    claimed_at: datetime | None = None,
    scheduled_start_at: datetime | None = None,
    candidate_timezone: str | None = None,
    day_windows_json: list[dict] | None = None,
    schedule_locked_at: datetime | None = None,
    with_default_schedule: bool = False,
    scenario_version_id: int | None = None,
    consent_version: str | None = None,
    consent_timestamp: datetime | None = None,
    ai_notice_version: str | None = None,
) -> CandidateSession:
    token = token or secrets.token_urlsafe(16)
    expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
    resolved_scheduled_start = scheduled_start_at
    resolved_timezone = candidate_timezone
    resolved_day_windows = day_windows_json
    if (
        with_default_schedule
        and resolved_scheduled_start is None
        and resolved_day_windows is None
    ):
        now_utc = datetime.now(UTC).replace(microsecond=0)
        resolved_scheduled_start = now_utc - timedelta(days=1)
        resolved_timezone = resolved_timezone or "UTC"
        # Keep all default test windows open around "now" so tests remain
        # deterministic even when strict day-window guards are enabled.
        open_window_start = now_utc - timedelta(days=1)
        open_window_end = now_utc + timedelta(days=1)
        resolved_day_windows = serialize_day_windows(
            [
                {
                    "dayIndex": day_index,
                    "windowStartAt": open_window_start,
                    "windowEndAt": open_window_end,
                }
                for day_index in range(1, 6)
            ]
        )

    resolved_scenario_version_id = (
        scenario_version_id
        if scenario_version_id is not None
        else simulation.active_scenario_version_id
    )
    if resolved_scenario_version_id is None:
        existing_scenario = (
            await session.execute(
                select(ScenarioVersion)
                .where(ScenarioVersion.simulation_id == simulation.id)
                .order_by(ScenarioVersion.version_index.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing_scenario is not None:
            resolved_scenario_version_id = existing_scenario.id
        else:
            scenario_version = ScenarioVersion(
                simulation_id=simulation.id,
                version_index=1,
                status="ready",
                storyline_md=f"# {simulation.title}",
                task_prompts_json=[],
                rubric_json={},
                focus_notes=simulation.focus or "",
                template_key=simulation.template_key,
                tech_stack=simulation.tech_stack,
                seniority=simulation.seniority,
            )
            session.add(scenario_version)
            await session.flush()
            resolved_scenario_version_id = scenario_version.id
        simulation.active_scenario_version_id = resolved_scenario_version_id
        await session.flush()

    cs = CandidateSession(
        simulation_id=simulation.id,
        scenario_version_id=resolved_scenario_version_id,
        candidate_user_id=None,
        candidate_name=candidate_name,
        invite_email=invite_email,
        token=token,
        candidate_email=candidate_email,
        candidate_auth0_sub=candidate_auth0_sub,
        claimed_at=claimed_at,
        status=status,
        expires_at=expires_at,
        started_at=started_at,
        completed_at=completed_at,
        scheduled_start_at=resolved_scheduled_start,
        candidate_timezone=resolved_timezone,
        day_windows_json=resolved_day_windows,
        schedule_locked_at=schedule_locked_at,
        consent_version=consent_version,
        consent_timestamp=(consent_timestamp if consent_version is not None else None)
        or (datetime.now(UTC) if consent_version is not None else None),
        ai_notice_version=(
            (ai_notice_version if ai_notice_version is not None else consent_version)
            if consent_version is not None
            else ai_notice_version
        ),
    )
    session.add(cs)
    await session.flush()
    return cs


async def create_submission(
    session: AsyncSession,
    *,
    candidate_session: CandidateSession,
    task: Task,
    content_text: str | None = None,
    content_json: dict[str, object] | None = None,
    submitted_at: datetime | None = None,
    tests_passed: int | None = None,
    tests_failed: int | None = None,
    test_output: str | None = None,
    code_repo_path: str | None = None,
    last_run_at: datetime | None = None,
    commit_sha: str | None = None,
    workflow_run_id: str | None = None,
    workflow_run_attempt: int | None = None,
    workflow_run_status: str | None = None,
    workflow_run_conclusion: str | None = None,
    workflow_run_completed_at: datetime | None = None,
    diff_summary_json: str | None = None,
    recording_id: int | None = None,
) -> Submission:
    submission = Submission(
        candidate_session_id=candidate_session.id,
        task_id=task.id,
        recording_id=recording_id,
        submitted_at=submitted_at or datetime.now(UTC),
        content_text=content_text,
        content_json=content_json,
        code_repo_path=code_repo_path,
        commit_sha=commit_sha,
        workflow_run_id=workflow_run_id,
        workflow_run_attempt=workflow_run_attempt,
        workflow_run_status=workflow_run_status,
        workflow_run_conclusion=workflow_run_conclusion,
        workflow_run_completed_at=workflow_run_completed_at,
        diff_summary_json=diff_summary_json,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        test_output=test_output,
        last_run_at=last_run_at,
    )
    session.add(submission)
    await session.flush()
    return submission


async def create_job(
    session: AsyncSession,
    *,
    company: Company,
    job_type: str = "test_job",
    status: str = "queued",
    idempotency_key: str | None = None,
    payload_json: dict | None = None,
    result_json: dict | None = None,
    last_error: str | None = None,
    attempt: int = 0,
    max_attempts: int = 5,
    candidate_session: CandidateSession | None = None,
    correlation_id: str | None = None,
    next_run_at: datetime | None = None,
) -> Job:
    job = Job(
        job_type=job_type,
        status=status,
        attempt=attempt,
        max_attempts=max_attempts,
        idempotency_key=idempotency_key or secrets.token_hex(12),
        payload_json=payload_json or {"ok": True},
        result_json=result_json,
        last_error=last_error,
        next_run_at=next_run_at,
        company_id=company.id,
        candidate_session_id=candidate_session.id if candidate_session else None,
        correlation_id=correlation_id,
    )
    session.add(job)
    await session.flush()
    return job
