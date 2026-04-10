"""Prompt override models shared across AI-backed Winoe features."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_serializer

AI_PROMPT_OVERRIDE_KEYS = (
    "prestart",
    "codespace",
    "day1",
    "day23",
    "day4",
    "day5",
    "winoeReport",
)
AI_AGENT_KEYS = AI_PROMPT_OVERRIDE_KEYS
_MAX_OVERRIDE_MARKDOWN_CHARS = 40_000


class AgentPromptOverride(BaseModel):
    """Optional prompt/rubric override for a single agent."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    instructions_md: str | None = Field(
        default=None,
        alias="instructionsMd",
        min_length=1,
        max_length=_MAX_OVERRIDE_MARKDOWN_CHARS,
    )
    rubric_md: str | None = Field(
        default=None,
        alias="rubricMd",
        min_length=1,
        max_length=_MAX_OVERRIDE_MARKDOWN_CHARS,
    )

    @model_serializer(mode="plain")
    def _serialize(self) -> dict[str, str]:
        data: dict[str, str] = {}
        if self.instructions_md is not None:
            data["instructionsMd"] = self.instructions_md
        if self.rubric_md is not None:
            data["rubricMd"] = self.rubric_md
        return data


class PromptOverrideSet(BaseModel):
    """Fixed-key override container persisted on companies and trials."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    prestart: AgentPromptOverride | None = None
    codespace: AgentPromptOverride | None = None
    day1: AgentPromptOverride | None = None
    day23: AgentPromptOverride | None = None
    day4: AgentPromptOverride | None = None
    day5: AgentPromptOverride | None = None
    winoe_report: AgentPromptOverride | None = Field(default=None, alias="winoeReport")

    @model_serializer(mode="plain")
    def _serialize(self) -> dict[str, dict[str, str]]:
        data: dict[str, dict[str, str]] = {}
        for key in AI_PROMPT_OVERRIDE_KEYS:
            field_name = "winoe_report" if key == "winoeReport" else key
            value = getattr(self, field_name, None)
            if value is not None:
                data[key] = value.model_dump(by_alias=True, exclude_none=True)
        return data


def normalize_prompt_override_payload(
    raw_value: Any,
) -> dict[str, dict[str, str]] | None:
    """Normalize prompt override payload for storage."""
    if raw_value is None:
        return None
    if hasattr(raw_value, "model_dump"):
        normalized = raw_value.model_dump(by_alias=True, exclude_none=True)
    elif isinstance(raw_value, dict):
        normalized = PromptOverrideSet.model_validate(raw_value).model_dump(
            by_alias=True,
            exclude_none=True,
        )
    else:
        return None
    return normalized or None


def merge_prompt_override_payloads(
    *,
    incoming: Any,
    fallback: Any = None,
) -> dict[str, dict[str, str]] | None:
    """Merge prompt override payloads with fixed-key replacement semantics."""
    if incoming is None:
        return normalize_prompt_override_payload(fallback)
    incoming_model = (
        incoming
        if isinstance(incoming, PromptOverrideSet)
        else PromptOverrideSet.model_validate(incoming)
    )
    merged = normalize_prompt_override_payload(fallback) or {}
    fields_set = getattr(incoming_model, "model_fields_set", set()) or set()
    for field_name in fields_set:
        key = "winoeReport" if field_name == "winoe_report" else field_name
        value = getattr(incoming_model, field_name)
        if value is None:
            merged.pop(key, None)
            continue
        merged[key] = value.model_dump(by_alias=True, exclude_none=True)
    return merged or None


__all__ = [
    "AI_AGENT_KEYS",
    "AI_PROMPT_OVERRIDE_KEYS",
    "AgentPromptOverride",
    "PromptOverrideSet",
    "merge_prompt_override_payloads",
    "normalize_prompt_override_payload",
]
