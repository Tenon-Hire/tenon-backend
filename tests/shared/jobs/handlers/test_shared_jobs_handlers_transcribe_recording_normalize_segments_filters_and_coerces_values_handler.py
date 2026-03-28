from __future__ import annotations

from tests.shared.jobs.handlers.shared_jobs_handlers_transcribe_recording_utils import *


def test_normalize_segments_filters_and_coerces_values():
    assert handler._normalize_segments(None) == []

    segments = handler._normalize_segments(
        [
            "skip-me",
            {"startMs": True, "endMs": 4.7, "text": " first "},
            {"startMs": " 12 ", "endMs": "oops", "text": "second"},
            {"startMs": 1, "endMs": 2},
        ]
    )
    assert segments == [
        {"startMs": 0, "endMs": 4, "text": "first"},
        {"startMs": 12, "endMs": 0, "text": "second"},
    ]
