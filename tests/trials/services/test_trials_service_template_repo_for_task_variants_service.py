from __future__ import annotations

from tests.trials.services.trials_core_service_utils import *


def test_template_repo_for_task_variants(monkeypatch):
    monkeypatch.setattr(sim_service.settings.github, "GITHUB_TEMPLATE_OWNER", "owner")
    monkeypatch.setattr(
        sim_service, "resolve_template_repo_full_name", lambda _key: "template-only"
    )
    repo = sim_service._template_repo_for_task(5, "code", "python-fastapi")
    assert repo == "template-only"
    # Day index 2 uses owner override when repo name lacks owner prefix
    repo_with_owner = sim_service._template_repo_for_task(2, "code", "python-fastapi")
    assert repo_with_owner.startswith("owner/")
    assert sim_service._template_repo_for_task(1, "design", "python-fastapi") is None
