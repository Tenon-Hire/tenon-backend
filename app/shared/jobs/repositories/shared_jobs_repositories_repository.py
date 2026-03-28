"""Application module for jobs repositories repository workflows."""

from __future__ import annotations

from app.shared.jobs.repositories import (
    shared_jobs_repositories_repository_create_get_repository as _create_get_module,
)
from app.shared.jobs.repositories import (
    shared_jobs_repositories_repository_create_update_many_recovery_repository as _create_update_many_recovery_module,
)
from app.shared.jobs.repositories import (
    shared_jobs_repositories_repository_create_update_many_repository as _create_update_many_module,
)
from app.shared.jobs.repositories import (
    shared_jobs_repositories_repository_create_update_repository as _create_update_module,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_claim_repository import (
    claim_next_runnable,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_lookup_repository import (
    get_by_id,
    get_by_id_for_principal,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_requeue_repository import (
    requeue_nonterminal_idempotent_job,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    MAX_JOB_ERROR_CHARS,
    MAX_JOB_PAYLOAD_BYTES,
    IdempotentJobSpec,
    sanitize_error,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    load_idempotent_job as _load_idempotent_job,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_specs_repository import (
    job_from_spec as _job_from_spec,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_specs_repository import (
    load_idempotent_jobs_for_keys as _load_idempotent_jobs_for_keys,
)
from app.shared.jobs.repositories.shared_jobs_repositories_repository_status_repository import (
    mark_dead_letter,
    mark_failed_and_reschedule,
    mark_succeeded,
)


async def create_or_get_idempotent(db, **kwargs):
    """Create or get idempotent."""
    _create_get_module.load_idempotent_job = _load_idempotent_job
    return await _create_get_module.create_or_get_idempotent(db, **kwargs)


async def create_or_update_idempotent(db, **kwargs):
    """Create or update idempotent."""
    _create_update_module.load_idempotent_job = _load_idempotent_job
    _create_update_module.create_or_get_idempotent = create_or_get_idempotent
    return await _create_update_module.create_or_update_idempotent(db, **kwargs)


async def create_or_update_many_idempotent(db, **kwargs):
    """Create or update many idempotent."""
    _create_update_many_module.load_idempotent_jobs_for_keys = (
        _load_idempotent_jobs_for_keys
    )
    _create_update_many_recovery_module.load_idempotent_job = _load_idempotent_job
    _create_update_many_recovery_module.load_idempotent_jobs_for_keys = (
        _load_idempotent_jobs_for_keys
    )
    return await _create_update_many_module.create_or_update_many_idempotent(
        db, **kwargs
    )


__all__ = [
    "IdempotentJobSpec",
    "MAX_JOB_ERROR_CHARS",
    "MAX_JOB_PAYLOAD_BYTES",
    "claim_next_runnable",
    "create_or_get_idempotent",
    "create_or_update_idempotent",
    "create_or_update_many_idempotent",
    "get_by_id",
    "get_by_id_for_principal",
    "mark_dead_letter",
    "mark_failed_and_reschedule",
    "mark_succeeded",
    "requeue_nonterminal_idempotent_job",
    "sanitize_error",
    "_job_from_spec",
    "_load_idempotent_job",
    "_load_idempotent_jobs_for_keys",
]
