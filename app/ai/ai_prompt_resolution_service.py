"""Prompt resolution helpers for system, company, simulation, and run context layers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _read_override_markdown(
    payload: Mapping[str, Any] | None,
    *,
    key: str,
) -> tuple[str | None, str | None]:
    if not isinstance(payload, Mapping):
        return None, None
    value = payload.get(key)
    if not isinstance(value, Mapping):
        return None, None
    instructions_md = value.get("instructionsMd")
    rubric_md = value.get("rubricMd")
    return (
        instructions_md.strip() if isinstance(instructions_md, str) else None,
        rubric_md.strip() if isinstance(rubric_md, str) else None,
    )


def resolve_prompt_layers(
    *,
    key: str,
    base_instructions_md: str,
    base_rubric_md: str,
    company_overrides_json: Mapping[str, Any] | None = None,
    simulation_overrides_json: Mapping[str, Any] | None = None,
    run_context_md: str | None = None,
) -> tuple[str, str]:
    """Resolve system base -> company -> simulation -> run context prompt order."""
    sections: list[str] = []
    rubric_sections: list[str] = []

    def _append(section_list: list[str], title: str, value: str | None) -> None:
        if isinstance(value, str) and value.strip():
            section_list.append(f"## {title}\n{value.strip()}")

    _append(sections, "System Base", base_instructions_md)
    _append(rubric_sections, "System Base", base_rubric_md)

    company_instructions, company_rubric = _read_override_markdown(
        company_overrides_json,
        key=key,
    )
    simulation_instructions, simulation_rubric = _read_override_markdown(
        simulation_overrides_json,
        key=key,
    )
    _append(sections, "Company Override", company_instructions)
    _append(rubric_sections, "Company Override", company_rubric)
    _append(sections, "Simulation Override", simulation_instructions)
    _append(rubric_sections, "Simulation Override", simulation_rubric)
    _append(sections, "Run Context", run_context_md)

    return "\n\n".join(sections).strip(), "\n\n".join(rubric_sections).strip()


def append_run_context_to_resolved_prompt(
    *,
    resolved_instructions_md: str,
    resolved_rubric_md: str,
    run_context_md: str | None = None,
) -> tuple[str, str]:
    """Append run context onto already-resolved base/company/simulation prompt text."""
    sections = [resolved_instructions_md.strip()]
    rubric_sections = [resolved_rubric_md.strip()] if resolved_rubric_md.strip() else []
    if isinstance(run_context_md, str) and run_context_md.strip():
        sections.append(f"## Run Context\n{run_context_md.strip()}")
    return "\n\n".join(sections).strip(), "\n\n".join(rubric_sections).strip()


__all__ = ["append_run_context_to_resolved_prompt", "resolve_prompt_layers"]
