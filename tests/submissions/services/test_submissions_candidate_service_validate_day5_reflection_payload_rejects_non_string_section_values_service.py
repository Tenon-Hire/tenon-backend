from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


def test_validate_day5_reflection_payload_rejects_non_string_section_values():
    day5_task = SimpleNamespace(type="reflection", day_index=5)
    reflection = _valid_day5_reflection_sections()
    reflection["tradeoffs"] = 123  # type: ignore[assignment]
    payload = SimpleNamespace(
        contentText="## Reflection summary", reflection=reflection
    )

    with pytest.raises(HTTPException) as excinfo:
        svc.validate_submission_payload(day5_task, payload)

    assert excinfo.value.status_code == 422
    fields = getattr(excinfo.value, "details", {}).get("fields", {})
    assert fields["reflection.tradeoffs"] == ["invalid_type"]
