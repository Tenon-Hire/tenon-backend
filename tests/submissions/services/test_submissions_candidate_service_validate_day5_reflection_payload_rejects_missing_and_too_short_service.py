from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


def test_validate_day5_reflection_payload_rejects_missing_and_too_short():
    day5_task = SimpleNamespace(type="reflection", day_index=5)
    payload = SimpleNamespace(
        contentText="## Reflection",
        reflection={
            "challenges": "too short",
            "decisions": " " * 3,
            "tradeoffs": (
                "Tradeoff discussion with enough detail to satisfy minimum length."
            ),
            "communication": (
                "Communication plan with enough detail to satisfy minimum length."
            ),
            # "next" intentionally missing
        },
    )

    with pytest.raises(HTTPException) as excinfo:
        svc.validate_submission_payload(day5_task, payload)
    assert excinfo.value.status_code == 422
    assert getattr(excinfo.value, "error_code", None) == "VALIDATION_ERROR"
    fields = getattr(excinfo.value, "details", {}).get("fields", {})
    assert fields["reflection.challenges"] == ["too_short"]
    assert fields["reflection.decisions"] == ["missing"]
    assert fields["reflection.next"] == ["missing"]
