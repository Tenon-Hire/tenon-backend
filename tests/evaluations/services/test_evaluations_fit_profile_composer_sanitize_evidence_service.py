from __future__ import annotations

from tests.evaluations.services.evaluations_fit_profile_composer_utils import *


def test_fit_profile_composer_sanitize_evidence():
    assert fit_profile_composer._sanitize_evidence("bad") is None
    assert fit_profile_composer._sanitize_evidence({"kind": "   "}) is None
    assert fit_profile_composer._sanitize_evidence(
        {"kind": "commit", "ref": " x "}
    ) == {
        "kind": "commit",
        "ref": "x",
    }
    assert fit_profile_composer._sanitize_evidence(
        {
            "kind": "transcript",
            "ref": "t:1",
            "startMs": -1,
            "endMs": 20,
            "excerpt": " hello ",
        }
    ) == {
        "kind": "transcript",
        "ref": "t:1",
        "endMs": 20,
        "excerpt": "hello",
    }
