from __future__ import annotations

from types import SimpleNamespace

from app.shared.utils.shared_utils_project_brief_service import (
    canonical_project_brief_markdown,
)
from app.trials.services.trials_services_trials_scenario_generation_story_service import (
    build_project_brief_markdown,
)


def test_canonical_project_brief_prefers_project_brief_md() -> None:
    scenario_version = SimpleNamespace(
        project_brief_md="# Project Brief\n\nUse this brief.",
        storyline_md="Do not use this fallback.",
    )

    assert canonical_project_brief_markdown(scenario_version) == (
        "# Project Brief\n\nUse this brief."
    )


def test_canonical_project_brief_normalizes_mapping_payloads() -> None:
    brief = canonical_project_brief_markdown(
        {
            "project_brief_md": {
                "business_context": "Help operators reconcile payments.",
                "system_requirements": "Build the workflow from scratch.",
                "technical_constraints": "Keep the stack open-ended.",
                "deliverables": ["Working code", "Tests"],
            }
        }
    )

    assert "## Business Context" in brief
    assert "Help operators reconcile payments." in brief
    assert "- Working code" in brief


def test_project_brief_generation_treats_preferred_language_as_context_only() -> None:
    brief = build_project_brief_markdown(
        role="Backend Engineer",
        focus="Scheduling operations",
        company_context={"preferredLanguageFramework": "TypeScript/Node"},
        preferred_language_framework="TypeScript/Node",
    )

    lowered = brief.lower()
    assert brief.startswith("# Project Brief")
    assert "preferred language/framework: typescript/node" in lowered
    assert "not as a requirement" in lowered
    assert "do not prescribe a specific framework" in lowered
    assert "starter" not in lowered
    assert "precommit" not in lowered
    assert "specializor" not in lowered
