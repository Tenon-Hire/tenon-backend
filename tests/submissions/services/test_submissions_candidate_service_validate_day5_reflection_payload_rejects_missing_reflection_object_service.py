from __future__ import annotations

import pytest

from tests.submissions.services.test_submissions_candidate_service_utils import *


def test_validate_day5_reflection_payload_accepts_markdown_only_reflection():
    day5_task = SimpleNamespace(type="reflection", day_index=5)
    payload = SimpleNamespace(contentText="## Reflection summary\n\nLearned a lot.")

    assert svc.validate_submission_payload(day5_task, payload) == {
        "kind": "day5_reflection",
        "markdown": "## Reflection summary\n\nLearned a lot.",
    }
