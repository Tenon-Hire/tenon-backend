"""Application module for init workflows."""

from app.shared.utils.shared_utils_lazy_module_aliases_utils import (
    LAZY_MODULE_ALIAS_EXEMPTIONS,
    resolve_lazy_module_alias,
)

_MODULE_ALIASES = {
    "models": "app.shared.jobs.repositories.shared_jobs_repositories_models_repository",
    "repository": "app.shared.jobs.repositories.shared_jobs_repositories_repository",
    "repository_claim": "app.shared.jobs.repositories.shared_jobs_repositories_repository_claim_repository",
    "repository_create_get": "app.shared.jobs.repositories.shared_jobs_repositories_repository_create_get_repository",
    "repository_create_update": "app.shared.jobs.repositories.shared_jobs_repositories_repository_create_update_repository",
    "repository_create_update_many": "app.shared.jobs.repositories.shared_jobs_repositories_repository_create_update_many_repository",
    "repository_create_update_many_recovery": "app.shared.jobs.repositories.shared_jobs_repositories_repository_create_update_many_recovery_repository",
    "repository_lookup": "app.shared.jobs.repositories.shared_jobs_repositories_repository_lookup_repository",
    "repository_requeue": "app.shared.jobs.repositories.shared_jobs_repositories_repository_requeue_repository",
    "repository_shared": "app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository",
    "repository_specs": "app.shared.jobs.repositories.shared_jobs_repositories_repository_specs_repository",
    "repository_status": "app.shared.jobs.repositories.shared_jobs_repositories_repository_status_repository",
}

LAZY_SHIM_EXEMPTION_REASON = LAZY_MODULE_ALIAS_EXEMPTIONS[__name__]

__all__ = sorted(_MODULE_ALIASES)


def __getattr__(name: str):  # pragma: no cover
    return resolve_lazy_module_alias(__name__, name, _MODULE_ALIASES, globals())
