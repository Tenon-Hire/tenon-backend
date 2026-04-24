"""Frozen AI policy snapshot helpers for scenario-version-level fairness."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from app.trials.constants.trials_constants_trials_ai_config_constants import (
    AI_NOTICE_DEFAULT_VERSION,
    default_ai_eval_enabled_by_day,
)
from app.trials.schemas.trials_schemas_trials_ai_values_schema import (
    resolve_trial_ai_fields,
)

from .ai_prompt_models import AI_AGENT_KEYS
from .ai_prompt_pack_service import PROMPT_PACK_VERSION, build_prompt_pack_entry
from .ai_prompt_resolution_service import (
    append_run_context_to_resolved_prompt,
    resolve_prompt_layers,
)
from .ai_runtime_config_service import (
    AIFeatureConfig,
    resolve_scenario_generation_config,
    resolve_winoe_report_aggregator_config,
    resolve_winoe_report_code_implementation_config,
    resolve_winoe_report_day1_config,
    resolve_winoe_report_day4_config,
    resolve_winoe_report_day5_config,
)

_ACTIVE_AGENT_KEYS = tuple(AI_AGENT_KEYS)
_AGENT_CONFIG_RESOLVERS = {
    "prestart": resolve_scenario_generation_config,
    "designDocReviewer": resolve_winoe_report_day1_config,
    "codeImplementationReviewer": resolve_winoe_report_code_implementation_config,
    "demoPresentationReviewer": resolve_winoe_report_day4_config,
    "reflectionEssayReviewer": resolve_winoe_report_day5_config,
    "winoeReport": resolve_winoe_report_aggregator_config,
}


class AIPolicySnapshotError(RuntimeError):
    """Raised when a scenario version is missing its frozen AI policy snapshot."""


def _snapshot_error(
    *,
    code: str,
    scenario_version_id: int | None = None,
    agent_key: str | None = None,
    details: dict[str, Any] | None = None,
) -> AIPolicySnapshotError:
    detail = code
    if scenario_version_id is not None:
        detail = f"{detail}:scenario_version:{scenario_version_id}"
    if agent_key is not None:
        detail = f"{detail}:agent:{agent_key}"
    exc = AIPolicySnapshotError(detail)
    exc.error_code = code
    exc.details = details or {}
    return exc


def _stable_json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_eval_enabled_by_day(raw_value: Any) -> dict[str, bool]:
    resolved = default_ai_eval_enabled_by_day()
    if not isinstance(raw_value, Mapping):
        return resolved
    for key in tuple(resolved):
        value = raw_value.get(key)
        if isinstance(value, bool):
            resolved[key] = value
    return resolved


def _build_candidate_settings(trial: object) -> dict[str, Any]:
    notice_version, notice_text, eval_enabled_by_day = resolve_trial_ai_fields(
        notice_version=getattr(trial, "ai_notice_version", None),
        notice_text=getattr(trial, "ai_notice_text", None),
        eval_enabled_by_day=getattr(trial, "ai_eval_enabled_by_day", None),
    )
    return {
        "noticeVersion": notice_version,
        "noticeText": notice_text,
        "evalEnabledByDay": eval_enabled_by_day,
    }


def _feature_config_for_agent(agent_key: str) -> AIFeatureConfig:
    resolver = _AGENT_CONFIG_RESOLVERS[agent_key]
    return resolver()


def _validate_runtime_payload(
    *,
    runtime: Any,
    scenario_version_id: int | None,
    agent_key: str,
) -> None:
    if not isinstance(runtime, Mapping):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_runtime_missing",
            scenario_version_id=scenario_version_id,
            agent_key=agent_key,
        )
    required_text_fields = ("runtimeMode", "provider", "model")
    for field in required_text_fields:
        if (
            not isinstance(runtime.get(field), str)
            or not str(runtime.get(field)).strip()
        ):
            raise _snapshot_error(
                code=f"scenario_version_ai_policy_snapshot_runtime_{field}_missing",
                scenario_version_id=scenario_version_id,
                agent_key=agent_key,
            )
    for field in ("timeoutSeconds", "maxRetries"):
        value = runtime.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            raise _snapshot_error(
                code=f"scenario_version_ai_policy_snapshot_runtime_{field}_missing",
                scenario_version_id=scenario_version_id,
                agent_key=agent_key,
            )
        if field == "timeoutSeconds" and value <= 0:
            raise _snapshot_error(
                code="scenario_version_ai_policy_snapshot_runtime_timeoutSeconds_missing",
                scenario_version_id=scenario_version_id,
                agent_key=agent_key,
            )
        if field == "maxRetries" and value < 0:
            raise _snapshot_error(
                code="scenario_version_ai_policy_snapshot_runtime_maxRetries_missing",
                scenario_version_id=scenario_version_id,
                agent_key=agent_key,
            )


def _validate_candidate_settings(
    *,
    candidate_settings: Any,
    scenario_version_id: int | None,
) -> None:
    if not isinstance(candidate_settings, Mapping):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_candidate_settings_missing",
            scenario_version_id=scenario_version_id,
        )
    for field in ("noticeVersion", "noticeText"):
        if (
            not isinstance(candidate_settings.get(field), str)
            or not str(candidate_settings.get(field)).strip()
        ):
            raise _snapshot_error(
                code=f"scenario_version_ai_policy_snapshot_candidate_settings_{field}_missing",
                scenario_version_id=scenario_version_id,
            )
    eval_enabled_by_day = candidate_settings.get("evalEnabledByDay")
    if not isinstance(eval_enabled_by_day, Mapping):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_candidate_settings_evalEnabledByDay_missing",
            scenario_version_id=scenario_version_id,
        )


def _validate_agent_snapshot_structure(
    *,
    agent_snapshot: Any,
    scenario_version_id: int | None,
    agent_key: str,
) -> None:
    if not isinstance(agent_snapshot, Mapping):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_agent_missing",
            scenario_version_id=scenario_version_id,
            agent_key=agent_key,
        )
    if agent_snapshot.get("key") != agent_key:
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_agent_key_mismatch",
            scenario_version_id=scenario_version_id,
            agent_key=agent_key,
            details={
                "expectedKey": agent_key,
                "actualKey": agent_snapshot.get("key"),
            },
        )
    for field_name in ("promptVersion", "rubricVersion"):
        if (
            not isinstance(agent_snapshot.get(field_name), str)
            or not str(agent_snapshot.get(field_name)).strip()
        ):
            raise _snapshot_error(
                code=f"scenario_version_ai_policy_snapshot_{field_name}_missing",
                scenario_version_id=scenario_version_id,
                agent_key=agent_key,
            )
    runtime = agent_snapshot.get("runtime")
    _validate_runtime_payload(
        runtime=runtime,
        scenario_version_id=scenario_version_id,
        agent_key=agent_key,
    )
    for field_name in (
        "policyFileName",
        "policySha256",
        "schemaFileName",
        "schemaSha256",
        "instructionsSha256",
        "rubricSha256",
        "resolvedInstructionsMd",
        "resolvedRubricMd",
    ):
        if (
            not isinstance(agent_snapshot.get(field_name), str)
            or not str(agent_snapshot.get(field_name)).strip()
        ):
            raise _snapshot_error(
                code=f"scenario_version_ai_policy_snapshot_{field_name}_missing",
                scenario_version_id=scenario_version_id,
                agent_key=agent_key,
            )


def validate_ai_policy_snapshot_contract(
    snapshot_json: Mapping[str, Any] | None,
    *,
    scenario_version_id: int | None = None,
) -> dict[str, Any]:
    """Validate the frozen AI policy snapshot contract and return a copy."""
    snapshot = require_ai_policy_snapshot(
        snapshot_json,
        scenario_version_id=scenario_version_id,
    )
    prompt_pack_version = snapshot.get("promptPackVersion")
    if not isinstance(prompt_pack_version, str) or not str(prompt_pack_version).strip():
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_prompt_pack_version_missing",
            scenario_version_id=scenario_version_id,
        )
    _validate_candidate_settings(
        candidate_settings=snapshot.get("candidateSettings"),
        scenario_version_id=scenario_version_id,
    )
    agents = snapshot.get("agents")
    if not isinstance(agents, Mapping):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_agents_missing",
            scenario_version_id=scenario_version_id,
        )
    actual_keys = {str(key) for key in agents if isinstance(key, str)}
    expected_keys = set(_ACTIVE_AGENT_KEYS)
    if actual_keys != expected_keys:
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_agent_contract_mismatch",
            scenario_version_id=scenario_version_id,
            details={
                "expectedAgentKeys": sorted(expected_keys),
                "actualAgentKeys": sorted(actual_keys),
            },
        )
    for agent_key in _ACTIVE_AGENT_KEYS:
        _validate_agent_snapshot_structure(
            agent_snapshot=agents.get(agent_key),
            scenario_version_id=scenario_version_id,
            agent_key=agent_key,
        )
    stored_digest = snapshot.get("snapshotDigest")
    computed_digest = _stable_json_hash(
        {key: value for key, value in snapshot.items() if key != "snapshotDigest"}
    )
    if not isinstance(stored_digest, str) or stored_digest != computed_digest:
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_digest_mismatch",
            scenario_version_id=scenario_version_id,
            details={
                "expectedDigest": computed_digest,
                "actualDigest": stored_digest,
            },
        )
    return dict(snapshot)


def validate_current_ai_policy_snapshot_contract(
    snapshot_json: Mapping[str, Any] | None,
    *,
    scenario_version_id: int | None = None,
) -> dict[str, Any]:
    """Validate a freshly emitted snapshot against the current prompt pack."""
    snapshot = validate_ai_policy_snapshot_contract(
        snapshot_json,
        scenario_version_id=scenario_version_id,
    )
    prompt_pack_version = snapshot.get("promptPackVersion")
    if prompt_pack_version != PROMPT_PACK_VERSION:
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_prompt_pack_version_mismatch",
            scenario_version_id=scenario_version_id,
            details={
                "expectedPromptPackVersion": PROMPT_PACK_VERSION,
                "actualPromptPackVersion": prompt_pack_version,
            },
        )
    for agent_key in _ACTIVE_AGENT_KEYS:
        prompt_entry = build_prompt_pack_entry(agent_key)
        agent_snapshot = snapshot["agents"][agent_key]
        if agent_snapshot.get("promptVersion") != prompt_entry.prompt_version:
            raise _snapshot_error(
                code="scenario_version_ai_policy_snapshot_prompt_version_mismatch",
                scenario_version_id=scenario_version_id,
                agent_key=agent_key,
                details={
                    "expectedPromptVersion": prompt_entry.prompt_version,
                    "actualPromptVersion": agent_snapshot.get("promptVersion"),
                },
            )
        if agent_snapshot.get("rubricVersion") != prompt_entry.rubric_version:
            raise _snapshot_error(
                code="scenario_version_ai_policy_snapshot_rubric_version_mismatch",
                scenario_version_id=scenario_version_id,
                agent_key=agent_key,
                details={
                    "expectedRubricVersion": prompt_entry.rubric_version,
                    "actualRubricVersion": agent_snapshot.get("rubricVersion"),
                },
            )
    return snapshot


def build_ai_policy_snapshot(
    *,
    trial: object,
    company_prompt_overrides_json: Mapping[str, Any] | None = None,
    trial_prompt_overrides_json: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical frozen AI policy snapshot for one scenario version."""
    agents: dict[str, Any] = {}
    for agent_key in _ACTIVE_AGENT_KEYS:
        prompt_entry = build_prompt_pack_entry(agent_key)
        resolved_instructions_md, resolved_rubric_md = resolve_prompt_layers(
            key=agent_key,
            base_instructions_md=prompt_entry.instructions_md,
            base_rubric_md=prompt_entry.rubric_md,
            company_overrides_json=company_prompt_overrides_json,
            trial_overrides_json=trial_prompt_overrides_json,
            run_context_md=None,
        )
        runtime_config = _feature_config_for_agent(agent_key)
        agents[agent_key] = {
            "key": agent_key,
            "provider": runtime_config.provider,
            "model": runtime_config.model,
            "promptVersion": prompt_entry.prompt_version,
            "rubricVersion": prompt_entry.rubric_version,
            "policyFileName": prompt_entry.policy_file_name,
            "policySha256": prompt_entry.policy_sha256,
            "schemaFileName": prompt_entry.schema_file_name,
            "schemaSha256": prompt_entry.schema_sha256,
            "instructionsSha256": prompt_entry.instructions_sha256,
            "rubricSha256": prompt_entry.rubric_sha256,
            "resolvedInstructionsMd": resolved_instructions_md,
            "resolvedRubricMd": resolved_rubric_md,
            "runtime": {
                "runtimeMode": runtime_config.runtime_mode,
                "provider": runtime_config.provider,
                "model": runtime_config.model,
                "timeoutSeconds": runtime_config.timeout_seconds,
                "maxRetries": runtime_config.max_retries,
            },
        }
    snapshot = {
        "promptPackVersion": PROMPT_PACK_VERSION,
        "candidateSettings": _build_candidate_settings(trial),
        "agents": agents,
    }
    snapshot["snapshotDigest"] = _stable_json_hash(snapshot)
    return snapshot


def compute_ai_policy_snapshot_digest(
    snapshot_json: Mapping[str, Any] | None,
) -> str | None:
    """Return the stable digest for a stored AI policy snapshot."""
    if not isinstance(snapshot_json, Mapping):
        return None
    if isinstance(snapshot_json.get("snapshotDigest"), str):
        return str(snapshot_json["snapshotDigest"])
    snapshot_copy = dict(snapshot_json)
    snapshot_copy.pop("snapshotDigest", None)
    return _stable_json_hash(snapshot_copy)


def compute_ai_policy_snapshot_basis_fingerprint(
    snapshot_json: Mapping[str, Any] | None,
) -> str:
    """Return a fixed-width fingerprint for any snapshot payload.

    This is intentionally stricter than the stored digest helper because the
    failed-run path must never trust an incoming snapshotDigest value that could
    exceed schema limits or be otherwise misleading.
    """
    if not isinstance(snapshot_json, Mapping):
        return _stable_json_hash({"snapshot": None})
    snapshot_copy = dict(snapshot_json)
    snapshot_copy.pop("snapshotDigest", None)
    return _stable_json_hash(snapshot_copy)


def require_ai_policy_snapshot(
    snapshot_json: Mapping[str, Any] | None,
    *,
    scenario_version_id: int | None = None,
) -> dict[str, Any]:
    """Return the stored snapshot or raise when it is missing."""
    if not isinstance(snapshot_json, Mapping):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_missing",
            scenario_version_id=scenario_version_id,
        )
    return dict(snapshot_json)


def get_agent_policy_snapshot(
    snapshot_json: Mapping[str, Any] | None,
    agent_key: str,
) -> dict[str, Any] | None:
    """Return one agent policy snapshot if present."""
    if not isinstance(snapshot_json, Mapping):
        return None
    agents = snapshot_json.get("agents")
    if not isinstance(agents, Mapping):
        return None
    value = agents.get(agent_key)
    if value is None and agent_key == "codeImplementationReviewer":
        value = agents.get("day23")
    return dict(value) if isinstance(value, Mapping) else None


def require_agent_policy_snapshot(
    snapshot_json: Mapping[str, Any] | None,
    agent_key: str,
    *,
    scenario_version_id: int | None = None,
) -> dict[str, Any]:
    """Return one agent policy snapshot or raise when it is missing."""
    snapshot = require_ai_policy_snapshot(
        snapshot_json,
        scenario_version_id=scenario_version_id,
    )
    agents = snapshot.get("agents")
    if not isinstance(agents, Mapping):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_agents_missing",
            scenario_version_id=scenario_version_id,
            agent_key=agent_key,
        )
    agent_snapshot = agents.get(agent_key)
    if agent_snapshot is None and agent_key == "codeImplementationReviewer":
        agent_snapshot = agents.get("day23")
    if not isinstance(agent_snapshot, Mapping):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_agent_missing",
            scenario_version_id=scenario_version_id,
            agent_key=agent_key,
        )
    return dict(agent_snapshot)


def require_agent_runtime(
    snapshot_json: Mapping[str, Any] | None,
    agent_key: str,
    *,
    scenario_version_id: int | None = None,
) -> dict[str, Any]:
    """Return stored runtime config for one agent or raise when invalid."""
    agent_snapshot = require_agent_policy_snapshot(
        snapshot_json,
        agent_key,
        scenario_version_id=scenario_version_id,
    )
    runtime = agent_snapshot.get("runtime")
    if not isinstance(runtime, Mapping):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_runtime_missing",
            scenario_version_id=scenario_version_id,
            agent_key=agent_key,
        )
    required_text_fields = ("runtimeMode", "provider", "model")
    for field in required_text_fields:
        if (
            not isinstance(runtime.get(field), str)
            or not str(runtime.get(field)).strip()
        ):
            raise _snapshot_error(
                code=f"scenario_version_ai_policy_snapshot_runtime_{field}_missing",
                scenario_version_id=scenario_version_id,
                agent_key=agent_key,
            )
    return dict(runtime)


def get_candidate_settings_from_snapshot(
    snapshot_json: Mapping[str, Any] | None,
) -> tuple[str | None, str | None, dict[str, bool] | None]:
    """Return frozen candidate-facing AI settings from a snapshot if present."""
    if not isinstance(snapshot_json, Mapping):
        return None, None, None
    candidate_settings = snapshot_json.get("candidateSettings")
    if not isinstance(candidate_settings, Mapping):
        return None, None, None
    notice_version = candidate_settings.get("noticeVersion")
    notice_text = candidate_settings.get("noticeText")
    eval_enabled_by_day = candidate_settings.get("evalEnabledByDay")
    return (
        notice_version if isinstance(notice_version, str) else None,
        notice_text if isinstance(notice_text, str) else None,
        _normalize_eval_enabled_by_day(eval_enabled_by_day)
        if isinstance(eval_enabled_by_day, Mapping)
        else None,
    )


def require_candidate_settings_from_snapshot(
    snapshot_json: Mapping[str, Any] | None,
    *,
    scenario_version_id: int | None = None,
) -> tuple[str, str, dict[str, bool]]:
    """Return frozen candidate-facing AI settings or raise when missing."""
    snapshot = validate_ai_policy_snapshot_contract(
        snapshot_json,
        scenario_version_id=scenario_version_id,
    )
    candidate_settings = snapshot.get("candidateSettings")
    if not isinstance(candidate_settings, Mapping):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_candidate_settings_missing",
            scenario_version_id=scenario_version_id,
        )
    return resolve_trial_ai_fields(
        notice_version=candidate_settings.get("noticeVersion"),
        notice_text=candidate_settings.get("noticeText"),
        eval_enabled_by_day=candidate_settings.get("evalEnabledByDay"),
        fallback_notice_version=AI_NOTICE_DEFAULT_VERSION,
        fallback_notice_text=None,
        fallback_eval_enabled_by_day=default_ai_eval_enabled_by_day(),
    )


def build_snapshot_prompt(
    *,
    snapshot_json: Mapping[str, Any] | None,
    agent_key: str,
    run_context_md: str | None = None,
) -> tuple[str, str] | None:
    """Return frozen prompt/rubric layers for one agent, plus run context."""
    validate_ai_policy_snapshot_contract(snapshot_json)
    agent_snapshot = get_agent_policy_snapshot(snapshot_json, agent_key)
    if agent_snapshot is None:
        return None
    instructions_md = agent_snapshot.get("resolvedInstructionsMd")
    rubric_md = agent_snapshot.get("resolvedRubricMd")
    if not isinstance(instructions_md, str) or not isinstance(rubric_md, str):
        return None
    return append_run_context_to_resolved_prompt(
        resolved_instructions_md=instructions_md,
        resolved_rubric_md=rubric_md,
        run_context_md=run_context_md,
    )


def build_required_snapshot_prompt(
    *,
    snapshot_json: Mapping[str, Any] | None,
    agent_key: str,
    run_context_md: str | None = None,
    scenario_version_id: int | None = None,
) -> tuple[str, str]:
    """Return frozen prompt/rubric layers for one agent or raise when missing."""
    validate_ai_policy_snapshot_contract(
        snapshot_json,
        scenario_version_id=scenario_version_id,
    )
    agent_snapshot = require_agent_policy_snapshot(
        snapshot_json,
        agent_key,
        scenario_version_id=scenario_version_id,
    )
    instructions_md = agent_snapshot.get("resolvedInstructionsMd")
    rubric_md = agent_snapshot.get("resolvedRubricMd")
    if not isinstance(instructions_md, str) or not isinstance(rubric_md, str):
        raise _snapshot_error(
            code="scenario_version_ai_policy_snapshot_prompt_missing",
            scenario_version_id=scenario_version_id,
            agent_key=agent_key,
        )
    return append_run_context_to_resolved_prompt(
        resolved_instructions_md=instructions_md,
        resolved_rubric_md=rubric_md,
        run_context_md=run_context_md,
    )


__all__ = [
    "AIPolicySnapshotError",
    "build_ai_policy_snapshot",
    "build_required_snapshot_prompt",
    "build_snapshot_prompt",
    "compute_ai_policy_snapshot_basis_fingerprint",
    "compute_ai_policy_snapshot_digest",
    "get_agent_policy_snapshot",
    "get_candidate_settings_from_snapshot",
    "require_agent_policy_snapshot",
    "require_agent_runtime",
    "require_ai_policy_snapshot",
    "require_candidate_settings_from_snapshot",
    "validate_ai_policy_snapshot_contract",
]
