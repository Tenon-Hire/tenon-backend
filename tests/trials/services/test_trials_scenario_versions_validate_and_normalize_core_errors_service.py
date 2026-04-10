from __future__ import annotations

import pytest

from tests.trials.services.trials_scenario_versions_service_utils import *


@pytest.mark.parametrize(
    ("merged_state", "detail_fragment"),
    [
        (
            {
                "storyline_md": 123,
                "task_prompts_json": [],
                "rubric_json": {},
                "focus_notes": "",
            },
            "storylineMd must be a string",
        ),
        (
            {
                "storyline_md": "x" * (MAX_SCENARIO_STORYLINE_CHARS + 1),
                "task_prompts_json": [],
                "rubric_json": {},
                "focus_notes": "",
            },
            "storylineMd exceeds",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [],
                "rubric_json": {},
                "focus_notes": 123,
            },
            "notes must be a string",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": [],
                "rubric_json": {},
                "focus_notes": "x" * (MAX_SCENARIO_NOTES_CHARS + 1),
            },
            "notes exceeds",
        ),
        (
            {
                "storyline_md": "ok",
                "task_prompts_json": {},
                "rubric_json": {},
                "focus_notes": "",
            },
            "taskPrompts must be an array",
        ),
    ],
)
def test_validate_and_normalize_core_error_branches(merged_state, detail_fragment):
    _assert_patch_invalid(merged_state, detail_fragment)
