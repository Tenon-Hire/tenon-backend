"""Application module for init workflows."""

from app.shared.utils.shared_utils_lazy_module_aliases_utils import (
    LAZY_MODULE_ALIAS_EXEMPTIONS,
    resolve_lazy_module_alias,
)

_MODULE_ALIASES = {
    "fit_profile": "app.submissions.repositories.submissions_repositories_submissions_fit_profile_model",
    "fit_profile_repository": "app.submissions.repositories.submissions_repositories_submissions_fit_profile_repository",
    "repository": "app.submissions.repositories.submissions_repositories_submissions_core_repository",
    "repository_handoff_upsert": "app.submissions.repositories.submissions_repositories_submissions_handoff_upsert_repository",
    "repository_handoff_write": "app.submissions.repositories.submissions_repositories_submissions_handoff_write_repository",
    "repository_lookup": "app.submissions.repositories.submissions_repositories_submissions_lookup_repository",
    "submission": "app.submissions.repositories.submissions_repositories_submissions_submission_model",
}

LAZY_SHIM_EXEMPTION_REASON = LAZY_MODULE_ALIAS_EXEMPTIONS[__name__]

__all__ = sorted(_MODULE_ALIASES)


def __getattr__(name: str):  # pragma: no cover
    return resolve_lazy_module_alias(__name__, name, _MODULE_ALIASES, globals())
