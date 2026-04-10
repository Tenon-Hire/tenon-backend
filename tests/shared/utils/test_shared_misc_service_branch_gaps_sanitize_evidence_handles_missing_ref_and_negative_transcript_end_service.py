from __future__ import annotations

from tests.shared.utils.shared_misc_service_branch_gaps_utils import *


def test_sanitize_evidence_handles_missing_ref_and_negative_transcript_end():
    # Covers missing ref branch.
    sanitized_no_ref = winoe_report_composer._sanitize_evidence(
        {"kind": "commit", "ref": 123}
    )
    assert sanitized_no_ref == {"kind": "commit"}

    # Covers transcript endMs rejected branch.
    sanitized_transcript = winoe_report_composer._sanitize_evidence(
        {"kind": "transcript", "startMs": 0, "endMs": -1}
    )
    assert sanitized_transcript == {
        "kind": "transcript",
        "startMs": 0,
        "endMs": 0,
    }
