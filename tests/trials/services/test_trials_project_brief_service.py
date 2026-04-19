from __future__ import annotations

from types import SimpleNamespace

from app.shared.utils.shared_utils_project_brief_service import (
    canonical_project_brief_markdown,
)
from app.trials.services.trials_services_trials_scenario_generation_story_service import (
    build_project_brief_markdown,
)


def test_canonical_project_brief_uses_new_string_payload() -> None:
    scenario_version = SimpleNamespace(
        project_brief_md="# Project Brief\n\n## Business Context\n\nA from-scratch build.\n",
        codespace_spec_json=None,
    )

    assert canonical_project_brief_markdown(scenario_version) == (
        "# Project Brief\n\n## Business Context\n\nA from-scratch build."
    )


def test_canonical_project_brief_normalizes_dict_project_brief_payload() -> None:
    scenario_version = SimpleNamespace(
        project_brief_md={
            "summary": "Build a candidate-facing workflow.",
            "candidateGoal": "Deliver the core system from scratch.",
            "acceptance_criteria": [
                "The repo ships with a working README.",
                "The implementation stays within the brief.",
            ],
        },
        codespace_spec_json=None,
    )

    project_brief_md = canonical_project_brief_markdown(scenario_version)

    assert project_brief_md.startswith("# Project Brief")
    assert "Build a candidate-facing workflow." in project_brief_md
    assert "Deliver the core system from scratch." in project_brief_md
    assert "The repo ships with a working README." in project_brief_md
    assert "The implementation stays within the brief." in project_brief_md


def test_canonical_project_brief_accepts_mapping_like_scenario_version() -> None:
    scenario_version = {
        "project_brief_md": {
            "summary": "Build a candidate-facing workflow.",
            "deliverables": ["Ship the README", "Keep the repo open-ended"],
        },
        "codespace_spec_json": {
            "summary": "Unused fallback",
        },
    }

    project_brief_md = canonical_project_brief_markdown(scenario_version)

    assert project_brief_md.startswith("# Project Brief")
    assert "Build a candidate-facing workflow." in project_brief_md
    assert "Ship the README" in project_brief_md
    assert "Keep the repo open-ended" in project_brief_md


def test_canonical_project_brief_derives_legacy_dict_payload() -> None:
    scenario_version = SimpleNamespace(
        project_brief_md=None,
        codespace_spec_json={
            "summary": "Build a candidate-facing workflow.",
            "candidate_goal": "Deliver the core system from scratch.",
            "acceptance_criteria": [
                "The repo ships with a working README.",
                "The implementation stays within the brief.",
            ],
        },
    )

    project_brief_md = canonical_project_brief_markdown(scenario_version)

    assert project_brief_md.startswith("# Project Brief")
    assert "Build a candidate-facing workflow." in project_brief_md
    assert "Deliver the core system from scratch." in project_brief_md
    assert "The repo ships with a working README." in project_brief_md
    assert "The implementation stays within the brief." in project_brief_md


def test_project_brief_generation_stays_stack_agnostic() -> None:
    project_brief_md = build_project_brief_markdown(
        role="Backend Engineer",
        company_context={"domain": "payments", "productArea": "billing"},
        focus="Improve invoice dispute handling.",
        preferred_language_framework="TypeScript/Node",
    )

    assert project_brief_md.startswith("# Project Brief")
    assert "python" not in project_brief_md.lower()
    assert "fastapi" not in project_brief_md.lower()
    assert "postgresql" not in project_brief_md.lower()
    assert "invoice-workflow" not in project_brief_md.lower()
    assert "company uses python internally" not in project_brief_md.lower()
    assert "template" not in project_brief_md.lower()
    assert "## Talent Partner Context" in project_brief_md
    assert "Preferred language/framework: TypeScript/Node" in project_brief_md
    assert "context only, not as a requirement" in project_brief_md


def test_project_brief_reads_preferred_language_framework_from_company_context() -> (
    None
):
    project_brief_md = build_project_brief_markdown(
        role="Backend Engineer",
        company_context={
            "domain": "payments",
            "preferredLanguageFramework": "Python/FastAPI",
        },
        focus=None,
    )

    assert "Preferred language/framework: Python/FastAPI" in project_brief_md
