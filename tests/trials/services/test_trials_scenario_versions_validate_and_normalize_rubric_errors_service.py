from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.parametrize(
    ("merged_state", "detail_fragment"),
    [
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [],
                "rubric_json": [],
                "focus_notes": "",
            },
            "rubric must be an object",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [],
                "rubric_json": {"x": "y" * (MAX_SCENARIO_RUBRIC_BYTES + 1)},
                "focus_notes": "",
            },
            "rubric exceeds",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [],
                "rubric_json": {"dayWeights": []},
                "focus_notes": "",
            },
            "dayWeights must be an object",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [],
                "rubric_json": {"dayWeights": {"a": 1}},
                "focus_notes": "",
            },
            "must map positive day indices",
        ),
    ],
)
def test_validate_and_normalize_rubric_error_branches(merged_state, detail_fragment):
    _assert_patch_invalid(merged_state, detail_fragment)
