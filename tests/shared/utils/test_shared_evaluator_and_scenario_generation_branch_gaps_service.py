from __future__ import annotations

from types import SimpleNamespace

from app.ai import build_ai_policy_snapshot
from app.evaluations.services import winoe_report_pipeline
from app.trials.services import scenario_generation


def _snapshot():
    trial = SimpleNamespace(
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={"1": True, "2": True, "3": True, "4": True, "5": True},
    )
    return build_ai_policy_snapshot(trial=trial)


def test_project_brief_generation_stays_open_ended():
    payload = scenario_generation.build_deterministic_template_scenario(
        role="Backend Engineer",
        tech_stack="Python",
        template_key="template-x",
        ai_policy_snapshot_json=_snapshot(),
    )
    assert payload.project_brief_md.startswith("# Project Brief")
    assert "template" not in payload.project_brief_md.lower()


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
