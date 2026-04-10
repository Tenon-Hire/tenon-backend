"""Structured output models used by runtime AI providers."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CodespaceSpec(BaseModel):
    """Structured repository specialization spec emitted by prestart generation."""

    model_config = ConfigDict(extra="forbid")

    task_kind: Literal[
        "feature", "bugfix", "debug", "migration", "optimization"
    ] = "feature"
    summary: str = Field(min_length=1, max_length=2_000)
    candidate_goal: str = Field(min_length=1, max_length=4_000)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=12)
    target_files: list[str] = Field(default_factory=list, max_length=25)
    repo_adjustments: list[str] = Field(default_factory=list, max_length=20)
    test_focus: list[str] = Field(default_factory=list, max_length=12)
    test_command: str | None = Field(default=None, max_length=500)


class ScenarioTaskPrompt(BaseModel):
    """Per-day scenario prompt payload that maps onto seeded task rows."""

    model_config = ConfigDict(extra="forbid")

    dayIndex: int = Field(ge=1, le=5)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10_000)


class ScenarioRubricDayWeights(BaseModel):
    """Fixed 5-day weighting contract for generated scenario rubrics."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    day1: int = Field(alias="1", ge=0, le=100)
    day2: int = Field(alias="2", ge=0, le=100)
    day3: int = Field(alias="3", ge=0, le=100)
    day4: int = Field(alias="4", ge=0, le=100)
    day5: int = Field(alias="5", ge=0, le=100)


class ScenarioRubricDimension(BaseModel):
    """Named rubric dimension with explanation and relative weight."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    weight: int = Field(ge=0, le=100)
    description: str = Field(min_length=1, max_length=2_000)


class ScenarioRubric(BaseModel):
    """Structured rubric contract for scenario generation."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=4_000)
    dayWeights: ScenarioRubricDayWeights
    dimensions: list[ScenarioRubricDimension] = Field(min_length=1, max_length=12)


class ScenarioGenerationOutput(BaseModel):
    """Strict output contract for the prestart creator agent."""

    model_config = ConfigDict(extra="forbid")

    storyline_md: str = Field(min_length=1, max_length=40_000)
    task_prompts_json: list[ScenarioTaskPrompt] = Field(min_length=5, max_length=5)
    rubric_json: ScenarioRubric
    codespace_spec_json: CodespaceSpec


class CodespacePatchProposal(BaseModel):
    """Strict output contract for the codespace specializer agent."""

    model_config = ConfigDict(extra="forbid")

    plan_md: str = Field(min_length=1, max_length=20_000)
    commit_message: str = Field(min_length=1, max_length=200)
    unified_diff: str = Field(min_length=1, max_length=500_000)


class EvidencePointer(BaseModel):
    """Evidence reference returned by reviewer models."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["submission", "diff", "transcript", "tests", "rubric"]
    ref: str = Field(min_length=1, max_length=500)
    quote: str | None = Field(default=None, max_length=1_500)
    dayIndex: int = Field(ge=1, le=5)


class DayReviewerOutput(BaseModel):
    """Strict output contract for each per-day reviewer model."""

    model_config = ConfigDict(extra="forbid")

    dayIndex: int = Field(ge=1, le=5)
    score: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=4_000)
    rubricBreakdown: dict[str, Any]
    evidence: list[EvidencePointer] = Field(default_factory=list, max_length=20)
    strengths: list[str] = Field(default_factory=list, max_length=8)
    risks: list[str] = Field(default_factory=list, max_length=8)


class AggregatorDayScore(BaseModel):
    """Aggregator-facing summary for a single day."""

    model_config = ConfigDict(extra="forbid")

    dayIndex: int = Field(ge=1, le=5)
    status: Literal["scored", "human_review_required"]
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    rubricBreakdown: dict[str, Any] | None = None
    evidence: list[EvidencePointer] = Field(default_factory=list)
    reason: str | None = Field(default=None, max_length=4_000)


class AggregatedWinoeReportOutput(BaseModel):
    """Strict output contract for the winoe-report aggregator agent."""

    model_config = ConfigDict(extra="forbid")

    overallWinoeScore: float = Field(ge=0.0, le=1.0)
    recommendation: Literal["strong_hire", "hire", "lean_hire", "no_hire"]
    confidence: float = Field(ge=0.0, le=1.0)
    dayScores: list[AggregatorDayScore] = Field(min_length=1, max_length=5)
    strengths: list[str] = Field(default_factory=list, max_length=10)
    risks: list[str] = Field(default_factory=list, max_length=10)
    calibrationText: str = Field(min_length=1, max_length=4_000)


__all__ = [
    "AggregatedWinoeReportOutput",
    "AggregatorDayScore",
    "CodespacePatchProposal",
    "CodespaceSpec",
    "DayReviewerOutput",
    "EvidencePointer",
    "ScenarioGenerationOutput",
    "ScenarioRubric",
    "ScenarioRubricDayWeights",
    "ScenarioRubricDimension",
    "ScenarioTaskPrompt",
]
