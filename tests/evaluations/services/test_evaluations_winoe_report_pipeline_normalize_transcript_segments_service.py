from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_pipeline_utils import *


def test_winoe_report_pipeline_normalize_transcript_segments():
    normalized = winoe_report_pipeline._normalize_transcript_segments(
        [
            "skip",
            {"startMs": 10, "endMs": 9, "text": "  message  "},
            {"start_ms": -20, "end_ms": 30, "content": "Alt keys"},
            {"start": 40.4, "end": 44.9, "excerpt": "From excerpt"},
            {"startMs": 100},  # missing end
            {"endMs": 200},  # missing start
        ]
    )

    assert normalized == [
        {"startMs": 10, "endMs": 10, "text": "  message  "},
        {"startMs": 0, "endMs": 30, "text": "Alt keys"},
        {"startMs": 40, "endMs": 44, "text": "From excerpt"},
    ]
