from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.ai import (
    build_ai_policy_snapshot,
    build_prompt_pack_entry,
    build_required_snapshot_prompt,
)

SOUL_PATH = Path("app/ai/prompt_assets/v1/SOUL.md")


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


def test_soul_markdown_exists_and_defines_required_sections() -> None:
    text = SOUL_PATH.read_text(encoding="utf-8")

    assert SOUL_PATH.is_file()
    for heading in (
        "## Identity",
        "## Archetype",
        "## Voice",
        "## Evaluation Philosophy",
        "## Boundaries",
        "## Required Language",
        "## Retired Terminology Ban",
        "## Winoe Report Rules",
    ):
        assert heading in text


def test_winoe_report_prompt_pack_entry_includes_soul_persona_governance() -> None:
    entry = build_prompt_pack_entry("winoeReport")

    assert "## Persona Governance" in entry.instructions_md
    assert (
        "I am Winoe. I help teams discover who will truly thrive"
        in entry.instructions_md
    )
    assert "The Talent Partner decides." in entry.instructions_md
    assert (
        "Use discovery/revelation language, not elimination/filtering language."
        in entry.instructions_md
    )
    assert (
        "Never say or imply that Winoe decides who should be hired."
        in entry.instructions_md
    )
    assert "Retired Terminology Ban" in entry.instructions_md


def test_winoe_report_snapshot_prompt_loads_soul_and_run_context() -> None:
    snapshot = build_ai_policy_snapshot(trial=_trial())
    system_prompt, _rubric_prompt = build_required_snapshot_prompt(
        snapshot_json=snapshot,
        agent_key="winoeReport",
        run_context_md="Candidate session ID: 101\nScenario version ID: 202",
        scenario_version_id=202,
    )

    assert "## Persona Governance" in system_prompt
    assert "The Evidence Trail supports..." in system_prompt
    assert "The Talent Partner has the evidence to decide..." in system_prompt
    assert (
        "Discovery/revelation language" in system_prompt
        or "discovery/revelation language" in system_prompt
    )
    assert "## Run Context" in system_prompt
    assert "Candidate session ID: 101" in system_prompt
