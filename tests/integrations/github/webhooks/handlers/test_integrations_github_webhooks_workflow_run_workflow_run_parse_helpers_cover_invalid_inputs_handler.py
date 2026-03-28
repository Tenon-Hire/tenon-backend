from __future__ import annotations

from tests.integrations.github.webhooks.handlers.integrations_github_webhooks_workflow_run_handler_utils import *


def test_workflow_run_parse_helpers_cover_invalid_inputs():
    assert workflow_run._normalized_lower(123) is None

    assert workflow_run._coerce_positive_int(object()) is None
    assert workflow_run._coerce_positive_int("not-int") is None
    assert workflow_run._coerce_positive_int("0") is None
    assert workflow_run._coerce_positive_int("-4") is None
    assert workflow_run._coerce_positive_int("42") == 42

    assert workflow_run._parse_github_datetime(None) is None
    assert workflow_run._parse_github_datetime("   ") is None
    assert workflow_run._parse_github_datetime("not-a-date") is None
    assert workflow_run._parse_github_datetime("2026-03-13T14:30:00") == datetime(
        2026,
        3,
        13,
        14,
        30,
        tzinfo=UTC,
    )
