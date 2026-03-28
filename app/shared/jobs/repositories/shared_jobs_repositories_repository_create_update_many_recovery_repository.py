"""Application module for jobs repositories repository create update many recovery repository workflows."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.jobs.repositories.shared_jobs_repositories_models_repository import Job
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    IdempotentJobSpec,
    load_idempotent_job,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_specs_repository import (
    job_from_spec,
    load_idempotent_jobs_for_keys,
)


async def recover_bulk_insert_conflicts(
    db: AsyncSession,
    *,
    company_id: int,
    new_specs: list[IdempotentJobSpec],
    existing_map: dict[tuple[str, str], Job],
) -> None:
    """Execute recover bulk insert conflicts."""
    try:
        await _insert_rows(db, company_id=company_id, new_specs=new_specs)
    except IntegrityError:
        await _recover_per_key(
            db, company_id=company_id, new_specs=new_specs, existing_map=existing_map
        )
        return
    created_map = await load_idempotent_jobs_for_keys(
        db,
        company_id=company_id,
        keys=[(spec.job_type, spec.idempotency_key) for spec in new_specs],
    )
    existing_map.update(created_map)


async def _insert_rows(
    db: AsyncSession, *, company_id: int, new_specs: list[IdempotentJobSpec]
) -> None:
    from sqlalchemy import insert

    from app.shared.jobs.repositories.shared_jobs_repositories_repository_specs_repository import (
        job_insert_row,
    )

    await db.execute(
        insert(Job),
        [job_insert_row(company_id=company_id, spec=spec) for spec in new_specs],
    )


async def _recover_per_key(
    db: AsyncSession,
    *,
    company_id: int,
    new_specs: list[IdempotentJobSpec],
    existing_map: dict[tuple[str, str], Job],
) -> None:
    for spec in new_specs:
        key = (spec.job_type, spec.idempotency_key)
        existing = await load_idempotent_job(
            db,
            company_id=company_id,
            job_type=spec.job_type,
            idempotency_key=spec.idempotency_key,
        )
        if existing is not None:
            existing_map[key] = existing
            continue
        job = job_from_spec(company_id=company_id, spec=spec)
        try:
            async with db.begin_nested():
                db.add(job)
                await db.flush()
        except IntegrityError:
            existing = await load_idempotent_job(
                db,
                company_id=company_id,
                job_type=spec.job_type,
                idempotency_key=spec.idempotency_key,
            )
            if existing is None:
                raise
            existing_map[key] = existing
            continue
        existing_map[key] = job
