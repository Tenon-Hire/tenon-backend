from __future__ import annotations

from tests.evaluations.services.evaluations_winoe_report_composer_utils import *


def test_winoe_report_composer_sanitize_evidence():
    assert winoe_report_composer._sanitize_evidence("bad") is None
    assert winoe_report_composer._sanitize_evidence({"kind": "   "}) is None
    assert winoe_report_composer._sanitize_evidence(
        {"kind": "commit", "ref": " x "}
    ) == {
        "kind": "commit",
        "ref": "x",
    }
    assert winoe_report_composer._sanitize_evidence(
        {
            "kind": "transcript",
            "ref": "t:1",
            "startMs": -1,
            "endMs": 20,
            "excerpt": " hello ",
            "label": " Handoff + Demo transcript ",
            "dimensionKey": " communication_handoff_demo ",
        }
    ) == {
        "kind": "transcript",
        "ref": "t:1",
        "startMs": 20,
        "endMs": 20,
        "excerpt": "hello",
        "label": "Handoff + Demo transcript",
        "dimensionKey": "communication_handoff_demo",
    }
    assert winoe_report_composer._sanitize_evidence(
        {
            "kind": "transcript",
            "ref": "t:2",
            "startMs": 12,
            "quote": " using quote ",
            "sourceLabel": " Day 4 ",
            "anchor": " timeline-4 ",
        }
    ) == {
        "kind": "transcript",
        "ref": "t:2",
        "startMs": 12,
        "endMs": 12,
        "excerpt": "using quote",
        "sourceLabel": "Day 4",
        "anchor": "timeline-4",
    }
