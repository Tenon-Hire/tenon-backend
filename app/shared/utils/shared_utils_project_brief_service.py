"""Application module for trials project brief normalization workflows."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def _field_value(value: Any, field_name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(field_name)
    return getattr(value, field_name, None)


def _string_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        markdown = value.get("markdown") or value.get("projectBriefMd")
        if isinstance(markdown, str) and markdown.strip():
            return markdown.strip()
        nested = value.get("project_brief_md") or value.get("projectBriefMd")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
        if isinstance(nested, Mapping):
            return _string_value(nested)
        derived = _legacy_brief_lines(value)
        if derived:
            return derived
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return str(value).strip()


def _legacy_brief_lines(legacy_brief: Mapping[str, Any]) -> str:
    lines = ["# Project Brief", ""]

    business_context = [
        str(legacy_brief.get(key) or "").strip()
        for key in (
            "business_context",
            "businessContext",
            "summary",
            "context",
        )
        if str(legacy_brief.get(key) or "").strip()
    ]
    system_requirements = [
        str(legacy_brief.get(key) or "").strip()
        for key in (
            "system_requirements",
            "systemRequirements",
            "candidate_goal",
            "candidateGoal",
            "goal",
        )
        if str(legacy_brief.get(key) or "").strip()
    ]
    technical_constraints = [
        str(legacy_brief.get(key) or "").strip()
        for key in (
            "technical_constraints",
            "technicalConstraints",
            "constraints",
        )
        if str(legacy_brief.get(key) or "").strip()
    ]
    deliverables = legacy_brief.get("deliverables") or legacy_brief.get(
        "acceptance_criteria"
    )

    if business_context:
        lines.extend(["## Business Context", "", *business_context, ""])
    if system_requirements:
        lines.extend(["## System Requirements", "", *system_requirements, ""])
    if technical_constraints:
        lines.extend(["## Technical Constraints", "", *technical_constraints, ""])
    if deliverables:
        lines.extend(["## Deliverables", ""])
        if isinstance(deliverables, str):
            lines.extend([f"- {deliverables.strip()}"])
        elif isinstance(deliverables, Mapping):
            lines.extend(
                f"- {str(value).strip()}"
                for value in deliverables.values()
                if str(value).strip()
            )
        else:
            lines.extend(
                f"- {str(item).strip()}" for item in deliverables if str(item).strip()
            )

    if len(lines) == 2:
        return ""
    return "\n".join(lines).strip()


def canonical_project_brief_markdown(
    scenario_version: Any,
    *,
    trial_title: str | None = None,
    storyline_md: str | None = None,
) -> str:
    """Return the canonical project brief markdown for a scenario version."""
    project_brief_md = _string_value(_field_value(scenario_version, "project_brief_md"))
    if project_brief_md:
        return project_brief_md

    fallback_context = (storyline_md or "").strip() or (
        trial_title.strip()
        if isinstance(trial_title, str) and trial_title.strip()
        else ""
    )
    if not fallback_context:
        fallback_context = (
            "A candidate-built system in an empty repository, scoped for a two-day "
            "implementation window."
        )
    return "\n".join(
        [
            "# Project Brief",
            "",
            "## Business Context",
            "",
            fallback_context,
            "",
            "## System Requirements",
            "",
            "Build the requested system from scratch in the empty workspace.",
            "",
            "## Technical Constraints",
            "",
            "- Keep the solution open-ended so multiple implementation approaches remain valid.",
            "- Do not rely on pre-populated implementation files.",
            "- Keep the scope realistic for two focused implementation days.",
            "",
            "## Deliverables",
            "",
            "- Working code and tests.",
            "- A clear README that explains the system and how to review it.",
        ]
    ).strip()


__all__ = ["canonical_project_brief_markdown"]
