from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_composer_utils import *


def test_build_ready_payload_uses_started_at_when_other_timestamps_missing():
    run = _run(
        generated_at=None,
        completed_at=None,
        started_at=datetime(2026, 3, 12, 9, 0),
    )
    payload = winoe_report_composer.build_ready_payload(run)
    assert payload["status"] == "ready"
    assert payload["generatedAt"] is not None
    assert payload["generatedAt"].tzinfo is not None
