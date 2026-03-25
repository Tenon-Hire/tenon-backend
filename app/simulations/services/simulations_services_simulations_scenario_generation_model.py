from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class ScenarioGenerationMetadata:
    source: str
    model_name: str | None
    model_version: str | None
    prompt_version: str
    rubric_version: str
    template_key: str


@dataclass(slots=True, frozen=True)
class GeneratedScenarioPayload:
    storyline_md: str
    task_prompts_json: list[dict[str, Any]]
    rubric_json: dict[str, Any]
    metadata: ScenarioGenerationMetadata


__all__ = ["GeneratedScenarioPayload", "ScenarioGenerationMetadata"]
