from __future__ import annotations

from types import SimpleNamespace

from app.ai import (
    build_ai_policy_snapshot,
    build_prompt_pack_entry,
    build_required_snapshot_prompt,
)


def _trial() -> SimpleNamespace:
    return SimpleNamespace(
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={
            "1": True,
            "2": True,
            "3": True,
            "4": True,
            "5": True,
        },
    )


def test_code_implementation_reviewer_rubric_uses_from_scratch_dimensions() -> None:
    entry = build_prompt_pack_entry("codeImplementationReviewer")

    assert "from-scratch Tech Trial" in entry.instructions_md
    assert "complete repository" in entry.instructions_md
    assert "complete commit history" in entry.instructions_md
    assert "file creation timeline" in entry.instructions_md
    assert "test coverage progression" in entry.instructions_md
    assert "AI tool usage is allowed" in entry.instructions_md
    assert "Do not penalize AI usage by itself" in entry.instructions_md

    assert "Project scaffolding quality - 18 points" in entry.rubric_md
    assert "Architectural coherence - 18 points" in entry.rubric_md
    assert "Code quality and maintainability - 17 points" in entry.rubric_md
    assert "Testing discipline - 15 points" in entry.rubric_md
    assert "Development process and commit history - 12 points" in entry.rubric_md
    assert "Documentation and handoff readiness - 10 points" in entry.rubric_md
    assert (
        "Requirements coverage and product completeness - 10 points" in entry.rubric_md
    )


def test_code_implementation_reviewer_prompt_asset_has_no_legacy_terms() -> None:
    entry = build_prompt_pack_entry("codeImplementationReviewer")
    combined = f"{entry.instructions_md}\n{entry.rubric_md}".lower()

    forbidden_terms = (
        "precommit " + "baseline",
        "delta from " + "precommit",
        "Special" + "izor",
    )
    for forbidden in forbidden_terms:
        assert forbidden not in combined


def test_code_implementation_reviewer_snapshot_prompt_mentions_required_evidence_sources() -> (
    None
):
    snapshot = build_ai_policy_snapshot(trial=_trial())
    system_prompt, rubric_prompt = build_required_snapshot_prompt(
        snapshot_json=snapshot,
        agent_key="codeImplementationReviewer",
        run_context_md="Candidate session ID: 101\nScenario version ID: 202",
        scenario_version_id=202,
    )

    assert "full repository" in system_prompt
    assert "complete commit history" in system_prompt
    assert "file creation timeline" in system_prompt
    assert "test coverage progression" in system_prompt
    assert "Evidence Trail" in system_prompt
    assert "AI tool usage is allowed" in system_prompt
    assert "from-scratch Tech Trial" in system_prompt
    assert "no pre-existing application code" in system_prompt
    assert "complete repository" in system_prompt
    assert "complete commit history" in system_prompt
    assert "Project scaffolding quality - 18 points" in rubric_prompt
    assert "Development process and commit history - 12 points" in rubric_prompt
    assert "Do not penalize AI usage by itself" in system_prompt
    assert "language or framework choice by itself" in system_prompt
    assert "bulk generation without engineering judgment" in system_prompt
