from __future__ import annotations

from app.evaluations.services import winoe_report_pipeline
from app.trials.services import scenario_generation


def test_template_display_name_handles_blank_catalog_value(monkeypatch):
    monkeypatch.setattr(
        scenario_generation, "TEMPLATE_CATALOG", {"template-x": {"display_name": "   "}}
    )
    assert scenario_generation._template_display_name("template-x") == "template-x"


def test_apply_generated_task_updates_covers_invalid_and_blank_inputs():
    tasks = [
        type(
            "Task",
            (),
            {
                "day_index": 1,
                "title": "Original 1",
                "description": "Original 1",
                "max_score": 5,
            },
        )(),
        type(
            "Task",
            (),
            {
                "day_index": 2,
                "title": "Original 2",
                "description": "Original 2",
                "max_score": 7,
            },
        )(),
    ]
    scenario_generation.apply_generated_task_updates(
        tasks=tasks,
        task_prompts_json=[
            {"dayIndex": "bad", "title": "Ignore", "description": "Ignore"},
            {"dayIndex": -1, "title": "Ignore", "description": "Ignore"},
            {"dayIndex": 1, "title": "  ", "description": "  "},
            {"dayIndex": 2, "title": "Updated", "description": "Updated"},
        ],
        rubric_json={"dayWeights": {"abc": "x", "1": 0, "2": 20}},
    )
    assert tasks[0].title == "Original 1"
    assert tasks[0].description == "Original 1"
    assert tasks[0].max_score == 5
    assert tasks[1].title == "Updated"
    assert tasks[1].description == "Updated"
    assert tasks[1].max_score == 20


def test_apply_generated_task_updates_handles_non_dict_day_weights():
    task = type(
        "Task",
        (),
        {"day_index": 3, "title": "Title", "description": "Desc", "max_score": 9},
    )()
    scenario_generation.apply_generated_task_updates(
        tasks=[task],
        task_prompts_json=[],
        rubric_json={"dayWeights": ["not", "a", "dict"]},
    )
    assert task.max_score == 9


def test_normalize_transcript_segments_keeps_text_when_present():
    normalized = winoe_report_pipeline._normalize_transcript_segments(
        [{"startMs": 1, "endMs": 2, "text": "hello"}]
    )
    assert normalized == [{"startMs": 1, "endMs": 2, "text": "hello"}]


def test_normalize_transcript_segments_allows_missing_text():
    normalized = winoe_report_pipeline._normalize_transcript_segments(
        [{"startMs": 1, "endMs": 2, "text": "   "}]
    )
    assert normalized == [{"startMs": 1, "endMs": 2}]
