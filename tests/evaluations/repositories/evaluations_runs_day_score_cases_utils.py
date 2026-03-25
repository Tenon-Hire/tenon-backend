from __future__ import annotations

import math

DAY_SCORE_PAYLOAD_ERROR_CASES: list[tuple[object, type[Exception], str]] = [
    ("invalid", ValueError, "sequence of objects"),
    ([], ValueError, "at least one day score"),
    ([123], ValueError, "must be an object"),
    (
        [
            {
                "day_index": 1,
                "score": 90,
                "rubric_results_json": {},
                "evidence_pointers_json": [],
            },
            {
                "day_index": 1,
                "score": 91,
                "rubric_results_json": {},
                "evidence_pointers_json": [],
            },
        ],
        ValueError,
        "duplicate day_index",
    ),
    (
        [
            {
                "day_index": True,
                "score": 90,
                "rubric_results_json": {},
                "evidence_pointers_json": [],
            }
        ],
        ValueError,
        "must be an integer",
    ),
    (
        [
            {
                "day_index": 7,
                "score": 90,
                "rubric_results_json": {},
                "evidence_pointers_json": [],
            }
        ],
        ValueError,
        "between 1 and 5",
    ),
    (
        [
            {
                "day_index": 2,
                "score": True,
                "rubric_results_json": {},
                "evidence_pointers_json": [],
            }
        ],
        ValueError,
        "must be numeric",
    ),
    (
        [
            {
                "day_index": 2,
                "score": math.nan,
                "rubric_results_json": {},
                "evidence_pointers_json": [],
            }
        ],
        ValueError,
        "must be finite",
    ),
    (
        [
            {
                "day_index": 2,
                "score": 90,
                "rubric_results_json": "bad",
                "evidence_pointers_json": [],
            }
        ],
        ValueError,
        "must be an object",
    ),
]


__all__ = [name for name in globals() if not name.startswith("__")]
