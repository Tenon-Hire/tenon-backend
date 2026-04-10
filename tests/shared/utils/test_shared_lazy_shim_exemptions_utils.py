from __future__ import annotations

import importlib
from types import ModuleType

import pytest

import app.shared.utils.shared_utils_lazy_module_aliases_utils as lazy_alias_utils

EXPECTED_EXEMPT_PACKAGES = [
    "app.candidates.candidate_sessions.repositories",
    "app.shared.jobs",
    "app.shared.jobs.repositories",
    "app.submissions.repositories",
    "app.submissions.services",
    "app.trials.repositories",
]


def test_lazy_shim_exemption_package_list_is_locked():
    assert (
        sorted(lazy_alias_utils.LAZY_MODULE_ALIAS_EXEMPTIONS)
        == EXPECTED_EXEMPT_PACKAGES
    )


@pytest.mark.parametrize("package_name", EXPECTED_EXEMPT_PACKAGES)
def test_lazy_shim_packages_expose_reason(package_name: str):
    package = importlib.import_module(package_name)

    assert (
        lazy_alias_utils.LAZY_MODULE_ALIAS_EXEMPTIONS[package_name]
        == package.LAZY_SHIM_EXEMPTION_REASON
    )
    assert isinstance(package._MODULE_ALIASES, dict)
    assert package._MODULE_ALIASES


@pytest.mark.parametrize("package_name", EXPECTED_EXEMPT_PACKAGES)
def test_lazy_shim_packages_resolve_and_cache_alias(package_name: str, monkeypatch):
    package = importlib.import_module(package_name)
    alias_name, module_path = next(iter(package._MODULE_ALIASES.items()))
    package.__dict__.pop(alias_name, None)

    imported: list[str] = []
    fake_module = ModuleType(f"{package_name}.fake_alias")

    def _fake_import_module(path: str) -> ModuleType:
        imported.append(path)
        return fake_module

    monkeypatch.setattr(lazy_alias_utils, "import_module", _fake_import_module)

    resolved = package.__getattr__(alias_name)

    assert resolved is fake_module
    assert package.__dict__[alias_name] is fake_module
    assert imported == [module_path]


@pytest.mark.parametrize("package_name", EXPECTED_EXEMPT_PACKAGES)
def test_lazy_shim_packages_reject_unknown_alias(package_name: str):
    package = importlib.import_module(package_name)
    missing_name = "__missing_wave_10_alias__"

    with pytest.raises(AttributeError) as exc_info:
        package.__getattr__(missing_name)

    message = str(exc_info.value)
    assert package_name in message
    assert missing_name in message
