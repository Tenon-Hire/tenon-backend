"""Application module for init workflows."""

from app.shared.utils.shared_utils_lazy_module_aliases_utils import (
    LAZY_MODULE_ALIAS_EXEMPTIONS,
    resolve_lazy_module_alias,
)

_MODULE_ALIASES = {
    "models": "app.candidates.candidate_sessions.repositories.candidates_candidate_sessions_repositories_candidates_candidate_sessions_core_model",
    "repository": "app.candidates.candidate_sessions.repositories.candidates_candidate_sessions_repositories_candidates_candidate_sessions_core_repository",
    "repository_basic": "app.candidates.candidate_sessions.repositories.candidates_candidate_sessions_repositories_candidates_candidate_sessions_basic_repository",
    "repository_day_audits": "app.candidates.candidate_sessions.repositories.candidates_candidate_sessions_repositories_candidates_candidate_sessions_day_audits_repository",
    "repository_tokens": "app.candidates.candidate_sessions.repositories.candidates_candidate_sessions_repositories_candidates_candidate_sessions_tokens_repository",
}

LAZY_SHIM_EXEMPTION_REASON = LAZY_MODULE_ALIAS_EXEMPTIONS[__name__]

__all__ = sorted(_MODULE_ALIASES)


def __getattr__(name: str):
    return resolve_lazy_module_alias(__name__, name, _MODULE_ALIASES, globals())
