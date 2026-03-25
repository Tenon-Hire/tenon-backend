from __future__ import annotations

from tests.integrations.github.template_health.test_integrations_github_template_health_service_utils import *


def test_is_dispatched_run_without_created_at():
    run = WorkflowRun(
        id=2,
        status="completed",
        conclusion="success",
        html_url="",
        head_sha="",
        event="workflow_dispatch",
        created_at=None,
    )
    assert template_health._is_dispatched_run(run, datetime.now(UTC)) is False
