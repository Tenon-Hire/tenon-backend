"""Application module for init workflows."""

from app.shared.utils.shared_utils_lazy_module_aliases_utils import (
    LAZY_MODULE_ALIAS_EXEMPTIONS,
    resolve_lazy_module_alias,
)

_MODULE_ALIASES = {
    "repository": "app.trials.repositories.trials_repositories_trials_core_repository",
    "repository_listing": "app.trials.repositories.trials_repositories_trials_listing_repository",
    "repository_owned": "app.trials.repositories.trials_repositories_trials_owned_repository",
    "trial": "app.trials.repositories.trials_repositories_trials_trial_model",
    "trial_status": "app.trials.repositories.trials_repositories_trials_trial_status_constants",
}

LAZY_SHIM_EXEMPTION_REASON = LAZY_MODULE_ALIAS_EXEMPTIONS[__name__]

__all__ = sorted(_MODULE_ALIASES)


def __getattr__(name: str):
    return resolve_lazy_module_alias(__name__, name, _MODULE_ALIASES, globals())
