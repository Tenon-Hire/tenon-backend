from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.parametrize(
    ("merged_state", "detail_fragment"),
    [
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [{"dayIndex": 1, "title": "a", "description": "b"}]
                * (MAX_SCENARIO_TASK_PROMPTS_BYTES // 8),
                "rubric_json": {},
                "focus_notes": "",
            },
            "taskPrompts exceeds",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": ["bad-item"],
                "rubric_json": {},
                "focus_notes": "",
            },
            "must be an object",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [{"title": "t", "description": "d"}],
                "rubric_json": {},
                "focus_notes": "",
            },
            "must include a positive integer dayIndex",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [
                    {"dayIndex": 1, "title": "t", "description": "d"},
                    {"dayIndex": 1, "title": "t2", "description": "d2"},
                ],
                "rubric_json": {},
                "focus_notes": "",
            },
            "duplicate dayIndex",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [{"dayIndex": 1, "title": "t"}],
                "rubric_json": {},
                "focus_notes": "",
            },
            "non-empty description",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [
                    {"dayIndex": 1, "title": "t", "description": "d", "type": ""}
                ],
                "rubric_json": {},
                "focus_notes": "",
            },
            "type must be a non-empty string",
        ),
    ],
)
def test_validate_and_normalize_task_prompt_error_branches(
    merged_state, detail_fragment
):
    _assert_patch_invalid(merged_state, detail_fragment)
