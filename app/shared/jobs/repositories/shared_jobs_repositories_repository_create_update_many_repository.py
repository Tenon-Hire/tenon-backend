"""Application module for jobs repositories repository create update many repository workflows."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import Job
from app.shared.jobs.repositories.shared_jobs_repositories_repository_create_update_many_recovery_repository import (
    recover_bulk_insert_conflicts,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    IdempotentJobSpec,
    apply_idempotent_job_updates,
    is_mutable_idempotent_job,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_specs_repository import (
    load_idempotent_jobs_for_keys,
    normalize_many_specs,
)


async def create_or_update_many_idempotent(
    db: AsyncSession,
    *,
    company_id: int,
    jobs: list[IdempotentJobSpec],
    commit: bool = True,
) -> list[Job]:
    """Create or update many idempotent."""
    normalized_specs = normalize_many_specs(jobs)
    if not normalized_specs:
        return []
    keys = [(spec.job_type, spec.idempotency_key) for spec in normalized_specs]
    existing_map = await load_idempotent_jobs_for_keys(
        db, company_id=company_id, keys=keys
    )
    new_specs = _apply_updates_to_existing(normalized_specs, existing_map)
    if new_specs:
        await recover_bulk_insert_conflicts(
            db, company_id=company_id, new_specs=new_specs, existing_map=existing_map
        )
    if commit:
        await db.commit()
    else:
        await db.flush()
    return _resolve_jobs_in_order(normalized_specs, existing_map)


def _apply_updates_to_existing(
    normalized_specs: list[IdempotentJobSpec], existing_map: dict[tuple[str, str], Job]
) -> list[IdempotentJobSpec]:
    new_specs: list[IdempotentJobSpec] = []
    for spec in normalized_specs:
        key = (spec.job_type, spec.idempotency_key)
        existing = existing_map.get(key)
        if existing is None:
            new_specs.append(spec)
            continue
        if is_mutable_idempotent_job(existing):
            apply_idempotent_job_updates(
                existing,
                payload_json=spec.payload_json,
                candidate_session_id=spec.candidate_session_id,
                max_attempts=spec.max_attempts,
                correlation_id=spec.correlation_id,
                next_run_at=spec.next_run_at,
            )
    return new_specs


def _resolve_jobs_in_order(
    normalized_specs: list[IdempotentJobSpec], existing_map: dict[tuple[str, str], Job]
) -> list[Job]:
    resolved_jobs: list[Job] = []
    for spec in normalized_specs:
        resolved = existing_map.get((spec.job_type, spec.idempotency_key))
        if resolved is not None:
            resolved_jobs.append(resolved)
    return resolved_jobs
