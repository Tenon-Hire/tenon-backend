from __future__ import annotations

from tests.submissions.services.test_submissions_candidate_service_utils import *


def test_validate_day5_reflection_payload_returns_structured_content_json():
    day5_task = SimpleNamespace(type="reflection", day_index=5)
    payload = SimpleNamespace(
        contentText="## Challenges\n...\n## Decisions\n...",
        reflection={
            "challenges": (
                "Handled API ambiguity by writing assumptions and validating early."
            ),
            "decisions": (
                "Chose clear request contracts and explicit error fields for FE."
            ),
            "tradeoffs": (
                "Prioritized deterministic validation over flexible free-form input."
            ),
            "communication": (
                "Documented constraints and highlighted known risks in handoff notes."
            ),
            "next": (
                "Would add richer rubric mapping and evaluator-side evidence pointers."
            ),
        },
    )

    result = svc.validate_submission_payload(day5_task, payload)
    assert result == {
        "kind": "day5_reflection",
        "markdown": "## Challenges\n...\n## Decisions\n...",
        "sections": {
            "challenges": (
                "Handled API ambiguity by writing assumptions and validating early."
            ),
            "decisions": (
                "Chose clear request contracts and explicit error fields for FE."
            ),
            "tradeoffs": (
                "Prioritized deterministic validation over flexible free-form input."
            ),
            "communication": (
                "Documented constraints and highlighted known risks in handoff notes."
            ),
            "next": (
                "Would add richer rubric mapping and evaluator-side evidence pointers."
            ),
        },
    }
