from __future__ import annotations

from app.ai import build_prompt_pack_entry


def test_code_implementation_reviewer_prompt_uses_from_scratch_evidence_model() -> None:
    entry = build_prompt_pack_entry("codeImplementationReviewer")
    prompt = f"{entry.instructions_md}\n\n{entry.rubric_md}".lower()

    for expected in (
        "complete repository",
        "complete commit history",
        "file creation timeline",
        "test coverage progression",
        "project scaffolding quality",
        "architectural coherence",
        "development process",
        "ai tool usage is allowed",
        "do not penalize ai usage by itself",
        "no pre-existing application code to compare against",
    ):
        assert expected in prompt

    for retired in (
        "precommit",
        "specializor",
        "starter template",
    ):
        assert retired not in prompt
