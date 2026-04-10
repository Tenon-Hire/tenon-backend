from __future__ import annotations

from tests.trials.services.trials_scenario_versions_service_utils import *


def test_build_edit_audit_payload_ignores_unchanged_fields():
    payload = scenario_service._build_edit_audit_payload(
        before={"storyline_md": "v1", "focus_notes": "same"},
        after={"storyline_md": "v2", "focus_notes": "same"},
        candidate_fields=["storyline_md", "focus_notes"],
    )
    assert payload == {
        "changedFields": ["storyline_md"],
        "before": {"storyline_md": "v1"},
        "after": {"storyline_md": "v2"},
    }
