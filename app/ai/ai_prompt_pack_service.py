"""Versioned base prompt pack loader backed by checked-in prompt assets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.ai.ai_output_models import (
    AggregatedWinoeReportOutput,
    CodespacePatchProposal,
    DayReviewerOutput,
    ScenarioGenerationOutput,
)


@dataclass(frozen=True, slots=True)
class PromptPackEntry:
    """Resolved base prompt/rubric entry for one agent."""

    key: str
    prompt_pack_version: str
    prompt_version: str
    rubric_version: str
    policy_file_name: str
    policy_sha256: str
    schema_file_name: str
    schema_sha256: str
    instructions_sha256: str
    rubric_sha256: str
    instructions_md: str
    rubric_md: str
    output_schema_json: dict[str, Any]
    output_model: type[Any]


@dataclass(frozen=True, slots=True)
class PromptPackBundle:
    """Fully loaded prompt pack manifest and entries."""

    version: str
    entries: dict[str, PromptPackEntry]


_OUTPUT_MODELS: dict[str, type[Any]] = {
    "ScenarioGenerationOutput": ScenarioGenerationOutput,
    "CodespacePatchProposal": CodespacePatchProposal,
    "DayReviewerOutput": DayReviewerOutput,
    "AggregatedWinoeReportOutput": AggregatedWinoeReportOutput,
}


def _prompt_assets_root() -> Path:
    return Path(__file__).resolve().parent / "prompt_assets" / "v1"


def _manifest_path() -> Path:
    return _prompt_assets_root() / "manifest.json"


def _prompt_asset_path(file_name: str) -> Path:
    return _prompt_assets_root() / file_name


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _extract_markdown_section(markdown_text: str, heading: str) -> str:
    marker = f"## {heading}".strip()
    lines = markdown_text.splitlines()
    start_index: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == marker:
            start_index = index + 1
            break
    if start_index is None:
        raise ValueError(f"Prompt asset missing '{marker}' section.")
    end_index = len(lines)
    for index in range(start_index, len(lines)):
        line = lines[index].strip()
        if line.startswith("## "):
            end_index = index
            break
    section = "\n".join(lines[start_index:end_index]).strip()
    if not section:
        raise ValueError(f"Prompt asset section '{marker}' cannot be blank.")
    return section


def _read_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Prompt asset JSON must be an object: {path.name}")
    return data


def _read_text_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Prompt asset file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def _normalize_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _load_persona_governance_md() -> str:
    return _read_text_file(_prompt_asset_path("SOUL.md"))


@lru_cache(maxsize=1)
def _load_prompt_pack_bundle() -> PromptPackBundle:
    manifest = _read_json_file(_manifest_path())
    version = str(manifest.get("version") or "").strip()
    if not version:
        raise ValueError("Prompt pack manifest must declare a version.")
    raw_agents = manifest.get("agents")
    if not isinstance(raw_agents, dict) or not raw_agents:
        raise ValueError("Prompt pack manifest must declare at least one agent.")

    entries: dict[str, PromptPackEntry] = {}
    assets_root = _prompt_assets_root()
    for key, raw_agent in raw_agents.items():
        if not isinstance(raw_agent, dict):
            raise ValueError(f"Prompt pack agent entry must be an object: {key}")
        policy_file_name = str(raw_agent.get("policyFile") or "").strip()
        schema_file_name = str(raw_agent.get("schemaFile") or "").strip()
        output_model_name = str(raw_agent.get("outputModel") or "").strip()
        if not policy_file_name or not schema_file_name or not output_model_name:
            raise ValueError(f"Prompt pack agent entry is incomplete: {key}")
        output_model = _OUTPUT_MODELS.get(output_model_name)
        if output_model is None:
            raise ValueError(
                f"Unsupported prompt pack output model: {output_model_name}"
            )

        policy_path = assets_root / policy_file_name
        schema_path = assets_root / schema_file_name
        policy_text = policy_path.read_text(encoding="utf-8")
        instructions_md = _extract_markdown_section(policy_text, "Instructions")
        rubric_md = _extract_markdown_section(policy_text, "Rubric")
        if key == "winoeReport":
            persona_governance_md = _load_persona_governance_md()
            instructions_md = (
                "## Persona Governance\n"
                f"{persona_governance_md}\n\n"
                f"{instructions_md}"
            )

        schema_json = _read_json_file(schema_path)
        expected_schema_json = output_model.model_json_schema()
        if _normalize_json(schema_json) != _normalize_json(expected_schema_json):
            raise ValueError(
                "Prompt pack schema file does not match output model "
                f"for agent '{key}'."
            )

        schema_text = _normalize_json(schema_json)
        entries[key] = PromptPackEntry(
            key=key,
            prompt_pack_version=version,
            prompt_version=f"{version}:{key}",
            rubric_version=f"{version}:{key}:rubric",
            policy_file_name=policy_file_name,
            policy_sha256=_hash_text(policy_text),
            schema_file_name=schema_file_name,
            schema_sha256=_hash_text(schema_text),
            instructions_sha256=_hash_text(instructions_md),
            rubric_sha256=_hash_text(rubric_md),
            instructions_md=instructions_md,
            rubric_md=rubric_md,
            output_schema_json=schema_json,
            output_model=output_model,
        )
    return PromptPackBundle(version=version, entries=entries)


PROMPT_PACK_VERSION = _load_prompt_pack_bundle().version


def build_prompt_pack_entry(agent_key: str) -> PromptPackEntry:
    """Return prompt pack entry for a supported agent key."""
    try:
        return _load_prompt_pack_bundle().entries[agent_key]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Unsupported AI prompt key: {agent_key}") from exc


__all__ = [
    "PROMPT_PACK_VERSION",
    "PromptPackBundle",
    "PromptPackEntry",
    "build_prompt_pack_entry",
]
