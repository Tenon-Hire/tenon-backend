"""Helpers for formally exempted lazy package-module aliases."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from importlib import import_module
from types import ModuleType

LAZY_MODULE_ALIAS_EXEMPTIONS: dict[str, str] = {
    "app.candidates.candidate_sessions.repositories": (
        "Eager alias imports trigger candidate-session repository/model cycles "
        "during startup and pytest bootstrap."
    ),
    "app.trials.repositories": (
        "Eager alias imports trigger trials/scenario repository cycles "
        "while trial models initialize."
    ),
    "app.shared.jobs": (
        "Eager alias imports create worker-runtime and handler/repository import "
        "cycles in job bootstrap."
    ),
    "app.shared.jobs.repositories": (
        "Eager alias imports create repository-helper and model import cycles "
        "during job repository bootstrap."
    ),
    "app.submissions.repositories": (
        "Eager alias imports trigger submissions repository/model cycles when "
        "routes and services import domain entrypoints."
    ),
    "app.submissions.services": (
        "Eager alias imports shadow callable service exports and regress runtime "
        "module-vs-callable behavior."
    ),
}

__all__ = ["LAZY_MODULE_ALIAS_EXEMPTIONS", "resolve_lazy_module_alias"]


def resolve_lazy_module_alias(
    package_name: str,
    alias_name: str,
    module_aliases: Mapping[str, str],
    package_globals: MutableMapping[str, object],
) -> ModuleType:
    """Resolve a lazy alias by importing the target module on first access."""
    module_path = module_aliases.get(alias_name)
    if module_path is None:
        raise AttributeError(f"module {package_name!r} has no attribute {alias_name!r}")
    module = import_module(module_path)
    package_globals[alias_name] = module
    return module
