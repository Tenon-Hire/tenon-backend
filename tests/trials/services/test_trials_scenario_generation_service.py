from __future__ import annotations

from types import SimpleNamespace

from app.trials.services import scenario_generation


def test_apply_generated_task_updates_sets_descriptions_and_scores() -> None:
    tasks = [
        SimpleNamespace(day_index=1, title="A", description="old", max_score=None),
        SimpleNamespace(day_index=2, title="B", description="old", max_score=None),
    ]
    prompts = [
        {"dayIndex": 1, "title": "Day 1", "description": "new day 1"},
        {"dayIndex": 2, "title": "Day 2", "description": "new day 2"},
    ]
    scenario_generation.apply_generated_task_updates(
        tasks=tasks,
        task_prompts_json=prompts,
        rubric_json={"dayWeights": {"1": 20, "2": 30}},
    )
    assert tasks[0].description == "new day 1"
    assert tasks[0].title == "Day 1"
    assert tasks[0].max_score == 20
    assert tasks[1].description == "new day 2"
    assert tasks[1].title == "Day 2"
    assert tasks[1].max_score == 30


def test_pick_returns_empty_string_for_empty_options() -> None:
    assert scenario_generation._pick((), seed=7, salt=1) == ""


def test_apply_generated_task_updates_ignores_invalid_day_weights() -> None:
    tasks = [SimpleNamespace(day_index=1, title="T1", description="D1", max_score=9)]
    scenario_generation.apply_generated_task_updates(
        tasks=tasks,
        task_prompts_json=[],
        rubric_json={"dayWeights": {"abc": "x", "1": "not-a-number"}},
    )
    assert tasks[0].max_score == 9
