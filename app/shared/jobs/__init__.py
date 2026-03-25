"""Background job processing package."""

from app.shared.utils.shared_utils_lazy_module_aliases_utils import (
    LAZY_MODULE_ALIAS_EXEMPTIONS,
    resolve_lazy_module_alias,
)

_MODULE_ALIASES = {
    "handlers": "app.shared.jobs.handlers",
    "repositories": "app.shared.jobs.repositories",
    "schemas": "app.shared.jobs.schemas",
    "worker": "app.shared.jobs.shared_jobs_worker_service",
    "worker_runtime": "app.shared.jobs.worker_runtime",
}

LAZY_SHIM_EXEMPTION_REASON = LAZY_MODULE_ALIAS_EXEMPTIONS[__name__]

__all__ = sorted(_MODULE_ALIASES)


def __getattr__(name: str):  # pragma: no cover
    return resolve_lazy_module_alias(__name__, name, _MODULE_ALIASES, globals())
