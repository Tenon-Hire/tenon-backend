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
                "rubric_json": {"dimensions": {}},
                "focus_notes": "",
            },
            "dimensions must be an array",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [],
                "rubric_json": {"dimensions": ["bad"]},
                "focus_notes": "",
            },
            "dimensions item must be an object",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [],
                "rubric_json": {
                    "dimensions": [{"name": "", "description": "d", "weight": 1}]
                },
                "focus_notes": "",
            },
            "name must be a non-empty string",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [],
                "rubric_json": {
                    "dimensions": [{"name": "n", "description": "", "weight": 1}]
                },
                "focus_notes": "",
            },
            "description must be a non-empty string",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [],
                "rubric_json": {
                    "dimensions": [{"name": "n", "description": "d", "weight": 0}]
                },
                "focus_notes": "",
            },
            "weight must be a positive integer",
        ),
    ],
)
def test_validate_and_normalize_dimensions_error_branches(
    merged_state, detail_fragment
):
    _assert_patch_invalid(merged_state, detail_fragment)
