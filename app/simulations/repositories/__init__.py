"""Application module for init workflows."""

from app.shared.utils.shared_utils_lazy_module_aliases_utils import (
    LAZY_MODULE_ALIAS_EXEMPTIONS,
    resolve_lazy_module_alias,
)

_MODULE_ALIASES = {
    "repository": "app.simulations.repositories.simulations_repositories_simulations_core_repository",
    "repository_listing": "app.simulations.repositories.simulations_repositories_simulations_listing_repository",
    "repository_owned": "app.simulations.repositories.simulations_repositories_simulations_owned_repository",
    "simulation": "app.simulations.repositories.simulations_repositories_simulations_simulation_model",
    "simulation_status": "app.simulations.repositories.simulations_repositories_simulations_simulation_status_constants",
}

LAZY_SHIM_EXEMPTION_REASON = LAZY_MODULE_ALIAS_EXEMPTIONS[__name__]

__all__ = sorted(_MODULE_ALIASES)


def __getattr__(name: str):
    return resolve_lazy_module_alias(__name__, name, _MODULE_ALIASES, globals())
