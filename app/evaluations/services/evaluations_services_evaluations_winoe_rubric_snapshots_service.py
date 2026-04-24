"""Materialize immutable Winoe rubric snapshots for scenario versions."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluations.repositories.evaluations_repositories_evaluations_rubric_snapshot_model import (
    RUBRIC_SNAPSHOT_SCOPE_COMPANY,
    RUBRIC_SNAPSHOT_SCOPE_WINOE,
    WinoeRubricSnapshot,
)
from app.evaluations.repositories.evaluations_repositories_evaluations_rubric_snapshot_repository import (
    create_rubric_snapshot,
    get_rubric_snapshot_by_identity,
    list_rubric_snapshots_for_scenario_version,
)
from app.trials.repositories.scenario_versions.trials_repositories_scenario_versions_trials_scenario_versions_model import (
    ScenarioVersion,
)
from app.trials.repositories.trials_repositories_trials_trial_model import Trial

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class WinoeRubricRegistryEntry:
    """Describe one baseline rubric asset."""

    rubric_key: str
    rubric_kind: str
    rubric_version: str
    source_path: str
    scope: str = RUBRIC_SNAPSHOT_SCOPE_WINOE


WINOE_RUBRIC_REGISTRY: tuple[WinoeRubricRegistryEntry, ...] = (
    WinoeRubricRegistryEntry(
        rubric_key="designDocReviewer",
        rubric_kind="day_1_design_doc",
        rubric_version="winoe-ai-pack-v1:designDocReviewer:rubric",
        source_path="app/ai/prompt_assets/v1/winoe-day-1-rubric.md",
    ),
    WinoeRubricRegistryEntry(
        rubric_key="codeImplementationReviewer",
        rubric_kind="day_2_3_code_implementation",
        rubric_version="winoe-ai-pack-v1:codeImplementationReviewer:rubric",
        source_path="app/ai/prompt_assets/v1/winoe-day-2&3-rubric.md",
    ),
    WinoeRubricRegistryEntry(
        rubric_key="demoPresentationReviewer",
        rubric_kind="day_4_demo",
        rubric_version="winoe-ai-pack-v1:demoPresentationReviewer:rubric",
        source_path="app/ai/prompt_assets/v1/winoe-day-4-rubric.md",
    ),
    WinoeRubricRegistryEntry(
        rubric_key="reflectionEssayReviewer",
        rubric_kind="day_5_reflection",
        rubric_version="winoe-ai-pack-v1:reflectionEssayReviewer:rubric",
        source_path="app/ai/prompt_assets/v1/winoe-day-5-rubric.md",
    ),
    WinoeRubricRegistryEntry(
        rubric_key="winoeReport",
        rubric_kind="winoe_synthesis",
        rubric_version="winoe-ai-pack-v1:winoeReport:rubric",
        source_path="app/ai/prompt_assets/v1/winoe-assessment-provider-rubric.md",
    ),
)

_REGISTRY_BY_KEY = {entry.rubric_key: entry for entry in WINOE_RUBRIC_REGISTRY}


class RubricSnapshotMaterializationError(RuntimeError):
    """Raised when rubric snapshot materialization fails."""


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_text_file(relative_path: str) -> str:
    path = _PROJECT_ROOT / relative_path
    if not path.is_file():
        raise RubricSnapshotMaterializationError(
            f"rubric source file not found: {relative_path}"
        )
    return path.read_text(encoding="utf-8").strip()


def _normalize_company_rubric_payload(
    trial: Trial, rubric_key: str, raw_value: Any
) -> tuple[str, str, str | None, dict[str, Any]]:
    if isinstance(raw_value, str):
        content = raw_value.strip()
        version = "company-v1"
        source_path = None
        metadata = {}
    elif isinstance(raw_value, Mapping):
        content = str(raw_value.get("content") or "").strip()
        version = str(
            raw_value.get("versionId") or raw_value.get("version") or ""
        ).strip()
        source_path = (
            str(raw_value.get("sourcePath")).strip()
            if isinstance(raw_value.get("sourcePath"), str)
            and str(raw_value.get("sourcePath")).strip()
            else None
        )
        metadata = dict(raw_value)
    else:
        raise RubricSnapshotMaterializationError(
            f"company rubric for '{rubric_key}' must be a string or object."
        )
    if not content:
        raise RubricSnapshotMaterializationError(
            f"company rubric for '{rubric_key}' cannot be blank."
        )
    if not version:
        version = f"company-trial-{trial.id}"
    return content, version, source_path, metadata


def _company_rubric_payload_by_key(trial: Trial) -> dict[str, Any]:
    raw_value = getattr(trial, "company_rubric_json", None)
    if not isinstance(raw_value, Mapping):
        return {}
    if isinstance(raw_value.get("rubrics"), Mapping):
        raw_rubrics = raw_value["rubrics"]
        return {
            str(key): value
            for key, value in raw_rubrics.items()
            if isinstance(key, str)
        }
    return {str(key): value for key, value in raw_value.items() if isinstance(key, str)}


async def _materialize_snapshot(
    db: AsyncSession,
    *,
    scenario_version_id: int,
    scope: str,
    rubric_kind: str,
    rubric_key: str,
    rubric_version: str,
    content_md: str,
    source_path: str | None,
    metadata_json: dict[str, Any] | None,
) -> WinoeRubricSnapshot:
    content_hash = hashlib.sha256(content_md.encode("utf-8")).hexdigest()
    existing = await get_rubric_snapshot_by_identity(
        db,
        scenario_version_id=scenario_version_id,
        scope=scope,
        rubric_kind=rubric_kind,
        rubric_key=rubric_key,
        rubric_version=rubric_version,
    )
    if existing is not None:
        return existing
    try:
        return await create_rubric_snapshot(
            db,
            scenario_version_id=scenario_version_id,
            scope=scope,
            rubric_kind=rubric_kind,
            rubric_key=rubric_key,
            rubric_version=rubric_version,
            content_hash=content_hash,
            content_md=content_md,
            source_path=source_path,
            metadata_json=metadata_json,
            commit=False,
        )
    except IntegrityError:
        await db.rollback()
        existing = await get_rubric_snapshot_by_identity(
            db,
            scenario_version_id=scenario_version_id,
            scope=scope,
            rubric_kind=rubric_kind,
            rubric_key=rubric_key,
            rubric_version=rubric_version,
        )
        if existing is None:
            raise
        return existing


def _effective_snapshot_payload(
    snapshot_json: Mapping[str, Any],
    rubric_snapshots: list[WinoeRubricSnapshot],
) -> dict[str, Any]:
    snapshot = copy.deepcopy(dict(snapshot_json))
    agents = snapshot.get("agents")
    if not isinstance(agents, Mapping):
        raise RubricSnapshotMaterializationError(
            "scenario version AI policy snapshot is missing agents."
        )
    snapshot["agents"] = {}
    snapshot_meta: list[dict[str, Any]] = []
    by_key: dict[str, WinoeRubricSnapshot] = {}
    for snapshot_row in rubric_snapshots:
        existing = by_key.get(snapshot_row.rubric_key)
        if existing is None:
            by_key[snapshot_row.rubric_key] = snapshot_row
            continue
        if (
            existing.scope != RUBRIC_SNAPSHOT_SCOPE_COMPANY
            and snapshot_row.scope == RUBRIC_SNAPSHOT_SCOPE_COMPANY
        ):
            by_key[snapshot_row.rubric_key] = snapshot_row
    for agent_key, agent_snapshot in agents.items():
        if not isinstance(agent_key, str):
            continue
        updated = dict(agent_snapshot) if isinstance(agent_snapshot, Mapping) else {}
        rubric_snapshot = by_key.get(agent_key)
        if rubric_snapshot is None:
            snapshot["agents"][agent_key] = updated
            continue
        updated["rubricVersion"] = rubric_snapshot.rubric_version
        updated["resolvedRubricMd"] = rubric_snapshot.content_md
        updated["rubricSnapshotId"] = rubric_snapshot.id
        updated["rubricSnapshotScope"] = rubric_snapshot.scope
        updated["rubricSnapshotKind"] = rubric_snapshot.rubric_kind
        updated["rubricSnapshotKey"] = rubric_snapshot.rubric_key
        updated["rubricSha256"] = rubric_snapshot.content_hash
        updated["sourcePath"] = rubric_snapshot.source_path
        snapshot["agents"][agent_key] = updated
        snapshot_meta.append(
            {
                "snapshotId": rubric_snapshot.id,
                "scenarioVersionId": rubric_snapshot.scenario_version_id,
                "rubricScope": rubric_snapshot.scope,
                "rubricKind": rubric_snapshot.rubric_kind,
                "rubricKey": rubric_snapshot.rubric_key,
                "rubricVersion": rubric_snapshot.rubric_version,
                "contentHash": rubric_snapshot.content_hash,
                "sourcePath": rubric_snapshot.source_path,
            }
        )
    snapshot["rubricSnapshots"] = sorted(
        snapshot_meta,
        key=lambda item: (
            str(item["rubricScope"]),
            str(item["rubricKind"]),
            str(item["rubricKey"]),
        ),
    )
    snapshot["snapshotDigest"] = _stable_hash(
        {key: value for key, value in snapshot.items() if key != "snapshotDigest"}
    )
    return snapshot


def _serialize_rubric_snapshots(
    rubric_snapshots: list[WinoeRubricSnapshot],
) -> list[dict[str, Any]]:
    return [
        {
            "snapshotId": snapshot.id,
            "scenarioVersionId": snapshot.scenario_version_id,
            "rubricScope": snapshot.scope,
            "rubricKind": snapshot.rubric_kind,
            "rubricKey": snapshot.rubric_key,
            "rubricVersion": snapshot.rubric_version,
            "contentHash": snapshot.content_hash,
            "sourcePath": snapshot.source_path,
        }
        for snapshot in rubric_snapshots
    ]


def _build_rubric_snapshot_context(
    *,
    scenario_version: ScenarioVersion,
    trial: Trial,
    rubric_snapshots: list[WinoeRubricSnapshot],
) -> dict[str, Any]:
    ordered_snapshots = sorted(
        rubric_snapshots,
        key=lambda item: (
            item.scope,
            item.rubric_kind,
            item.rubric_key,
            item.rubric_version,
            item.id,
        ),
    )
    source_snapshot_json = dict(scenario_version.ai_policy_snapshot_json or {})
    effective_snapshot = _effective_snapshot_payload(
        source_snapshot_json,
        ordered_snapshots,
    )
    return {
        "scenarioVersionId": scenario_version.id,
        "trialId": trial.id,
        "aiPolicySnapshotJson": source_snapshot_json,
        "effectiveAiPolicySnapshotJson": effective_snapshot,
        "snapshots": ordered_snapshots,
        "rubricSnapshots": _serialize_rubric_snapshots(ordered_snapshots),
    }


async def materialize_scenario_version_rubric_snapshots(
    db: AsyncSession,
    *,
    scenario_version: ScenarioVersion,
    trial: Trial | None = None,
) -> dict[str, Any]:
    """Materialize rubric snapshots and return effective snapshot context."""
    resolved_trial = trial or scenario_version.trial
    if resolved_trial is None:
        raise RubricSnapshotMaterializationError(
            "trial is required to materialize rubric snapshots."
        )
    company_payload = _company_rubric_payload_by_key(resolved_trial)
    snapshot_rows: list[WinoeRubricSnapshot] = []
    for entry in WINOE_RUBRIC_REGISTRY:
        content_md = _read_text_file(entry.source_path)
        snapshot_rows.append(
            await _materialize_snapshot(
                db,
                scenario_version_id=scenario_version.id,
                scope=entry.scope,
                rubric_kind=entry.rubric_kind,
                rubric_key=entry.rubric_key,
                rubric_version=entry.rubric_version,
                content_md=content_md,
                source_path=entry.source_path,
                metadata_json={
                    "sourceType": "winoe_static_file",
                    "registryKey": entry.rubric_key,
                },
            )
        )
        raw_company = company_payload.get(entry.rubric_key)
        if raw_company is None:
            continue
        (
            company_content,
            company_version,
            company_source_path,
            company_metadata,
        ) = _normalize_company_rubric_payload(
            resolved_trial, entry.rubric_key, raw_company
        )
        snapshot_rows.append(
            await _materialize_snapshot(
                db,
                scenario_version_id=scenario_version.id,
                scope=RUBRIC_SNAPSHOT_SCOPE_COMPANY,
                rubric_kind=entry.rubric_kind,
                rubric_key=entry.rubric_key,
                rubric_version=company_version,
                content_md=company_content,
                source_path=company_source_path,
                metadata_json={
                    "sourceType": "company_trial_attachment",
                    "registryKey": entry.rubric_key,
                    "trialId": resolved_trial.id,
                    "companyMetadata": company_metadata,
                },
            )
        )
    await db.flush()
    return _build_rubric_snapshot_context(
        scenario_version=scenario_version,
        trial=resolved_trial,
        rubric_snapshots=snapshot_rows,
    )


async def get_rubric_snapshots_for_scenario_version(
    db: AsyncSession,
    *,
    scenario_version: ScenarioVersion,
    trial: Trial | None = None,
) -> dict[str, Any]:
    """Return existing snapshots or materialize them when missing."""
    scenario_version_id = getattr(scenario_version, "id", None)
    resolved_trial = trial or getattr(scenario_version, "trial", None)
    if not isinstance(scenario_version_id, int):
        source_snapshot_json = dict(scenario_version.ai_policy_snapshot_json or {})
        return {
            "scenarioVersionId": scenario_version_id,
            "trialId": getattr(resolved_trial, "id", None),
            "aiPolicySnapshotJson": source_snapshot_json,
            "effectiveAiPolicySnapshotJson": _effective_snapshot_payload(
                source_snapshot_json,
                [],
            ),
            "snapshots": [],
            "rubricSnapshots": [],
        }
    snapshots = await list_rubric_snapshots_for_scenario_version(
        db, scenario_version_id=scenario_version_id
    )
    if snapshots:
        if resolved_trial is None:
            raise RubricSnapshotMaterializationError(
                "trial is required to materialize rubric snapshots."
            )
        return _build_rubric_snapshot_context(
            scenario_version=scenario_version,
            trial=resolved_trial,
            rubric_snapshots=snapshots,
        )
    return await materialize_scenario_version_rubric_snapshots(
        db, scenario_version=scenario_version, trial=trial
    )


__all__ = [
    "RUBRIC_SNAPSHOT_SCOPE_COMPANY",
    "RUBRIC_SNAPSHOT_SCOPE_WINOE",
    "RubricSnapshotMaterializationError",
    "WINOE_RUBRIC_REGISTRY",
    "WinoeRubricRegistryEntry",
    "get_rubric_snapshots_for_scenario_version",
    "materialize_scenario_version_rubric_snapshots",
]
