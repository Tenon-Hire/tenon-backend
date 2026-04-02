"""Codespace specializer orchestration, invite gating, and job helpers."""

from __future__ import annotations

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import (
    allow_demo_or_test_mode,
    require_agent_runtime,
)
from app.shared.database.shared_database_models_model import ScenarioVersion, Simulation, Task
from app.shared.jobs.repositories import repository as jobs_repo
from app.shared.utils.shared_utils_errors_utils import ApiError
from app.simulations.repositories.scenario_versions.simulations_repositories_scenario_versions_simulations_scenario_versions_model import (
    SCENARIO_VERSION_STATUS_READY,
    SCENARIO_VERSION_STATUS_LOCKED,
)
from app.simulations.services.simulations_services_simulations_codespace_specializer_runtime_service import (
    build_demo_bundle_artifact,
    generate_codespace_bundle_artifact,
)
from app.tasks.services.tasks_services_tasks_template_catalog_service import (
    resolve_template_repo_full_name,
)
from app.submissions.repositories.precommit_bundles import repository_lookup as bundle_lookup_repo
from app.submissions.repositories.precommit_bundles import repository_write as bundle_write_repo
from app.submissions.repositories.precommit_bundles.submissions_repositories_precommit_bundles_submissions_precommit_bundles_core_model import (
    PRECOMMIT_BUNDLE_STATUS_DISABLED,
    PRECOMMIT_BUNDLE_STATUS_FAILED,
    PRECOMMIT_BUNDLE_STATUS_GENERATING,
    PRECOMMIT_BUNDLE_STATUS_READY,
)

CODESPACE_SPECIALIZER_JOB_TYPE = "codespace_specializer"


def build_codespace_specializer_payload(
    *,
    simulation_id: int,
    scenario_version_id: int,
) -> dict[str, int]:
    """Build job payload for a locked scenario version."""
    return {
        "simulationId": int(simulation_id),
        "scenarioVersionId": int(scenario_version_id),
    }


def codespace_specializer_idempotency_key(scenario_version_id: int) -> str:
    """Return the durable job idempotency key for a scenario version."""
    return f"scenario:{scenario_version_id}:codespace_specializer"


def has_coding_tasks(tasks: list[Task] | list[object]) -> bool:
    """Return whether the simulation needs a codespace baseline bundle."""
    return any(_is_coding_task(task) for task in tasks)


async def ensure_precommit_bundle_ready_for_invites(
    db: AsyncSession,
    *,
    simulation: Simulation,
    scenario_version: ScenarioVersion,
    tasks: list[Task] | list[object],
) -> object | None:
    """Ensure a locked coding scenario has a ready bundle before inviting."""
    if not has_coding_tasks(tasks):
        return None
    template_key = _template_key_for_bundle(scenario_version)
    ready_bundle = await bundle_lookup_repo.get_ready_by_scenario_and_template(
        db,
        scenario_version_id=scenario_version.id,
        template_key=template_key,
    )
    if ready_bundle is not None:
        return ready_bundle

    existing = await bundle_lookup_repo.get_by_scenario_and_template(
        db,
        scenario_version_id=scenario_version.id,
        template_key=template_key,
    )
    bundle_status = getattr(existing, "status", None)
    if bundle_status == PRECOMMIT_BUNDLE_STATUS_FAILED:
        await db.commit()
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Codespace baseline generation failed for the locked scenario.",
            error_code="PRECOMMIT_BUNDLE_FAILED",
            retryable=False,
            details={
                "scenarioVersionId": scenario_version.id,
                "bundleStatus": bundle_status,
                "lastError": getattr(existing, "last_error", None),
            },
        )
    if bundle_status == PRECOMMIT_BUNDLE_STATUS_DISABLED:
        await db.commit()
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Codespace bundle generation is disabled for this scenario.",
            error_code="PRECOMMIT_BUNDLE_DISABLED",
            retryable=False,
            details={
                "scenarioVersionId": scenario_version.id,
                "bundleStatus": bundle_status,
            },
        )

    raise ApiError(
        status_code=status.HTTP_409_CONFLICT,
        detail="Codespace baseline is not ready for the locked scenario.",
        error_code="PRECOMMIT_BUNDLE_NOT_READY",
        retryable=True,
        details={
            "scenarioVersionId": scenario_version.id,
            "bundleStatus": bundle_status or "missing",
        },
    )


async def ensure_precommit_bundle_prepared_for_approved_scenario(
    db: AsyncSession,
    *,
    simulation: Simulation,
    scenario_version: ScenarioVersion,
    tasks: list[Task] | list[object],
) -> object | None:
    """Start bundle generation immediately after approval for coding scenarios."""
    if not has_coding_tasks(tasks):
        return None
    template_key = _template_key_for_bundle(scenario_version)
    ready_bundle = await bundle_lookup_repo.get_ready_by_scenario_and_template(
        db,
        scenario_version_id=scenario_version.id,
        template_key=template_key,
    )
    if ready_bundle is not None:
        return ready_bundle

    existing = await bundle_lookup_repo.get_by_scenario_and_template(
        db,
        scenario_version_id=scenario_version.id,
        template_key=template_key,
    )
    bundle_status = getattr(existing, "status", None)
    if bundle_status in {
        PRECOMMIT_BUNDLE_STATUS_GENERATING,
        PRECOMMIT_BUNDLE_STATUS_FAILED,
        PRECOMMIT_BUNDLE_STATUS_DISABLED,
    }:
        return existing

    template_repo_full_name = resolve_codespace_template_repo(
        tasks,
        template_key=template_key,
    )
    runtime = require_agent_runtime(
        getattr(scenario_version, "ai_policy_snapshot_json", None),
        "codespace",
        scenario_version_id=scenario_version.id,
    )
    runtime_mode = str(runtime["runtimeMode"])
    if allow_demo_or_test_mode(runtime_mode):
        artifact = build_demo_bundle_artifact(
            scenario_version=scenario_version,
            template_repo_full_name=template_repo_full_name,
        )
        return await _persist_ready_bundle(
            db,
            scenario_version=scenario_version,
            template_key=template_key,
            artifact=artifact,
            existing_bundle=existing,
            commit=False,
        )

    if existing is None:
        existing = await bundle_write_repo.create_bundle(
            db,
            scenario_version_id=scenario_version.id,
            template_key=template_key,
            status=PRECOMMIT_BUNDLE_STATUS_GENERATING,
            commit=False,
        )
    else:
        existing = await bundle_write_repo.update_bundle(
            db,
            bundle=existing,
            status=PRECOMMIT_BUNDLE_STATUS_GENERATING,
            last_error="",
            commit=False,
        )
    await enqueue_codespace_specializer_job(
        db,
        simulation_id=simulation.id,
        scenario_version_id=scenario_version.id,
        company_id=simulation.company_id,
        commit=False,
    )
    return existing


async def enqueue_codespace_specializer_job(
    db: AsyncSession,
    *,
    simulation_id: int,
    scenario_version_id: int,
    company_id: int,
    commit: bool = True,
):
    """Create or reuse the specialization job for an approved scenario version."""
    return await jobs_repo.create_or_get_idempotent(
        db,
        job_type=CODESPACE_SPECIALIZER_JOB_TYPE,
        idempotency_key=codespace_specializer_idempotency_key(scenario_version_id),
        payload_json=build_codespace_specializer_payload(
            simulation_id=simulation_id,
            scenario_version_id=scenario_version_id,
        ),
        company_id=company_id,
        correlation_id=f"scenario:{scenario_version_id}",
        max_attempts=1,
        commit=commit,
    )


async def run_codespace_specializer_job(
    db: AsyncSession,
    *,
    simulation_id: int,
    scenario_version_id: int,
) -> dict[str, object]:
    """Run one codespace specialization job and persist bundle state."""
    simulation = (
        await db.execute(
            select(Simulation)
            .where(Simulation.id == simulation_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if simulation is None:
        return {"status": "simulation_not_found", "simulationId": simulation_id}
    scenario_version = (
        await db.execute(
            select(ScenarioVersion)
            .where(ScenarioVersion.id == scenario_version_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if scenario_version is None or scenario_version.simulation_id != simulation.id:
        return {
            "status": "scenario_version_not_found",
            "simulationId": simulation_id,
            "scenarioVersionId": scenario_version_id,
        }

    if getattr(scenario_version, "status", None) not in {
        SCENARIO_VERSION_STATUS_READY,
        SCENARIO_VERSION_STATUS_LOCKED,
    }:
        return {
            "status": "scenario_not_approved",
            "simulationId": simulation_id,
            "scenarioVersionId": scenario_version_id,
            "scenarioStatus": getattr(scenario_version, "status", None),
        }

    tasks = (
        (
            await db.execute(
                select(Task)
                .where(Task.simulation_id == simulation.id)
                .order_by(Task.day_index.asc())
            )
        )
        .scalars()
        .all()
    )
    if not has_coding_tasks(tasks):
        return {
            "status": "skipped_non_coding_simulation",
            "simulationId": simulation_id,
            "scenarioVersionId": scenario_version_id,
        }

    template_key = _template_key_for_bundle(scenario_version)
    bundle = await bundle_lookup_repo.get_by_scenario_and_template(
        db,
        scenario_version_id=scenario_version.id,
        template_key=template_key,
    )
    if bundle is None:
        bundle = await bundle_write_repo.create_bundle(
            db,
            scenario_version_id=scenario_version.id,
            template_key=template_key,
            status=PRECOMMIT_BUNDLE_STATUS_GENERATING,
            commit=False,
        )
    else:
        await bundle_write_repo.update_bundle(
            db,
            bundle=bundle,
            status=PRECOMMIT_BUNDLE_STATUS_GENERATING,
            last_error="",
            commit=False,
        )

    template_repo_full_name = resolve_codespace_template_repo(
        tasks,
        template_key=template_key,
    )
    try:
        runtime = require_agent_runtime(
            getattr(scenario_version, "ai_policy_snapshot_json", None),
            "codespace",
            scenario_version_id=scenario_version.id,
        )
        runtime_mode = str(runtime["runtimeMode"])
        if allow_demo_or_test_mode(runtime_mode):
            artifact = build_demo_bundle_artifact(
                scenario_version=scenario_version,
                template_repo_full_name=template_repo_full_name,
            )
        else:
            artifact = await generate_codespace_bundle_artifact(
                template_repo_full_name=template_repo_full_name,
                scenario_version=scenario_version,
                simulation=simulation,
            )
        bundle = await _persist_ready_bundle(
            db,
            scenario_version=scenario_version,
            template_key=template_key,
            artifact=artifact,
            existing_bundle=bundle,
            commit=False,
        )
        await db.commit()
        await db.refresh(bundle)
        return {
            "status": "completed",
            "simulationId": simulation.id,
            "scenarioVersionId": scenario_version.id,
            "bundleId": bundle.id,
            "bundleStatus": bundle.status,
        }
    except Exception as exc:
        await bundle_write_repo.update_bundle(
            db,
            bundle=bundle,
            status=PRECOMMIT_BUNDLE_STATUS_FAILED,
            patch_text=None,
            storage_ref=None,
            commit_message=None,
            model_name=None,
            model_version=None,
            prompt_version=None,
            test_summary_json=None,
            provenance_json=None,
            last_error=str(exc),
            commit=False,
        )
        await db.commit()
        raise


def resolve_codespace_template_repo(
    tasks: list[Task] | list[object],
    *,
    template_key: str,
) -> str:
    """Return the canonical template repo backing the shared coding workspace."""
    for task in tasks:
        if _is_coding_task(task):
            template_repo = (getattr(task, "template_repo", "") or "").strip()
            if template_repo:
                return template_repo
    return resolve_template_repo_full_name(template_key)


def _is_coding_task(task: object) -> bool:
    task_type = (getattr(task, "type", "") or "").strip().lower()
    return getattr(task, "day_index", None) in {2, 3} and task_type in {"code", "debug"}


def _template_key_for_bundle(scenario_version: ScenarioVersion) -> str:
    template_key = (getattr(scenario_version, "template_key", "") or "").strip()
    if not template_key:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            detail="Locked scenario version is missing a template key.",
            error_code="PRECOMMIT_BUNDLE_TEMPLATE_KEY_MISSING",
            retryable=False,
            details={"scenarioVersionId": scenario_version.id},
        )
    return template_key


async def _persist_ready_bundle(
    db: AsyncSession,
    *,
    scenario_version: ScenarioVersion,
    template_key: str,
    artifact,
    existing_bundle=None,
    commit: bool,
):
    bundle = existing_bundle or await bundle_lookup_repo.get_by_scenario_and_template(
        db,
        scenario_version_id=scenario_version.id,
        template_key=template_key,
    )
    if bundle is None:
        return await bundle_write_repo.create_bundle(
            db,
            scenario_version_id=scenario_version.id,
            template_key=template_key,
            status=PRECOMMIT_BUNDLE_STATUS_READY,
            patch_text=artifact.patch_payload_json,
            base_template_sha=artifact.base_template_sha,
            commit_message=artifact.commit_message,
            model_name=artifact.model_name,
            model_version=artifact.model_version,
            prompt_version=artifact.prompt_version,
            test_summary_json=artifact.test_summary_json,
            provenance_json=artifact.provenance_json,
            last_error="",
            commit=commit,
        )
    return await bundle_write_repo.update_bundle(
        db,
        bundle=bundle,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=artifact.patch_payload_json,
        storage_ref=None,
        base_template_sha=artifact.base_template_sha,
        commit_message=artifact.commit_message,
        model_name=artifact.model_name,
        model_version=artifact.model_version,
        prompt_version=artifact.prompt_version,
        test_summary_json=artifact.test_summary_json,
        provenance_json=artifact.provenance_json,
        last_error="",
        commit=commit,
    )


__all__ = [
    "CODESPACE_SPECIALIZER_JOB_TYPE",
    "build_codespace_specializer_payload",
    "codespace_specializer_idempotency_key",
    "enqueue_codespace_specializer_job",
    "ensure_precommit_bundle_prepared_for_approved_scenario",
    "ensure_precommit_bundle_ready_for_invites",
    "has_coding_tasks",
    "resolve_codespace_template_repo",
    "run_codespace_specializer_job",
]
