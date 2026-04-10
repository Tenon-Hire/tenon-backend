"""Application module for trials services trials scenario generation model workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class ScenarioGenerationMetadata:
    """Represent scenario generation metadata data and behavior."""

    source: str
    model_name: str | None
    model_version: str | None
    prompt_version: str
    rubric_version: str
    template_key: str


@dataclass(slots=True, frozen=True)
class GeneratedScenarioPayload:
    """Represent generated scenario payload data and behavior."""

    storyline_md: str
    task_prompts_json: list[dict[str, Any]]
    rubric_json: dict[str, Any]
    codespace_spec_json: dict[str, Any]
    ai_policy_snapshot_json: dict[str, Any] | None
    metadata: ScenarioGenerationMetadata


__all__ = ["GeneratedScenarioPayload", "ScenarioGenerationMetadata"]
