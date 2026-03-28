"""Application module for candidates candidate sessions services candidates candidate sessions day close jobs upsert service workflows."""

from __future__ import annotations

from app.shared.database.shared_database_models_model import Job
from app.shared.jobs.repositories import repository as jobs_repo


def _dedupe_job_specs(
    specs: list[jobs_repo.IdempotentJobSpec],
) -> list[jobs_repo.IdempotentJobSpec]:
    deduped: dict[tuple[str, str], jobs_repo.IdempotentJobSpec] = {}
    for spec in specs:
        deduped[(spec.job_type, spec.idempotency_key)] = spec
    return list(deduped.values())


async def _upsert_day_close_jobs(
    db,
    *,
    company_id: int,
    specs: list[jobs_repo.IdempotentJobSpec],
) -> list[Job]:
    if not specs:
        return []
    return await jobs_repo.create_or_update_many_idempotent(
        db,
        company_id=company_id,
        jobs=_dedupe_job_specs(specs),
        commit=False,
    )


__all__ = ["_upsert_day_close_jobs"]
