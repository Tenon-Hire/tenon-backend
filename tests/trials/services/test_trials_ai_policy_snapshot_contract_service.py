from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ai import (
    AIPolicySnapshotError,
    build_ai_policy_snapshot,
    compute_ai_policy_snapshot_basis_fingerprint,
    compute_ai_policy_snapshot_digest,
    validate_ai_policy_snapshot_contract,
)


def _trial():
    return SimpleNamespace(
        ai_notice_version="mvp1",
        ai_notice_text="AI assistance may be used for evaluation support.",
        ai_eval_enabled_by_day={
            "1": True,
            "2": True,
            "3": True,
            "4": True,
            "5": True,
        },
    )


def test_build_ai_policy_snapshot_uses_only_active_agents():
    snapshot = build_ai_policy_snapshot(trial=_trial())

    assert set(snapshot["agents"]) == {
        "prestart",
        "designDocReviewer",
        "codeImplementationReviewer",
        "demoPresentationReviewer",
        "reflectionEssayReviewer",
        "winoeReport",
    }
    assert "codespace" not in snapshot["agents"]
    assert snapshot["agents"]["winoeReport"]["provider"]
    assert snapshot["agents"]["winoeReport"]["model"]
    assert snapshot["agents"]["winoeReport"]["runtime"]["provider"]


def test_validate_ai_policy_snapshot_contract_rejects_retired_agent():
    snapshot = build_ai_policy_snapshot(trial=_trial())
    snapshot["agents"]["codespace"] = {
        "key": "codespace",
        "promptVersion": "legacy",
        "rubricVersion": "legacy",
        "runtime": {
            "runtimeMode": "test",
            "provider": "openai",
            "model": "gpt-4.1",
        },
    }

    with pytest.raises(
        AIPolicySnapshotError,
        match="scenario_version_ai_policy_snapshot_agent_contract_mismatch",
    ):
        validate_ai_policy_snapshot_contract(snapshot)


def test_validate_ai_policy_snapshot_contract_accepts_version_mismatch_when_snapshot_is_self_consistent():
    snapshot = build_ai_policy_snapshot(trial=_trial())
    snapshot["promptPackVersion"] = "legacy-pack"
    snapshot["agents"]["prestart"]["promptVersion"] = "legacy-prestart"
    snapshot["agents"]["prestart"]["rubricVersion"] = "legacy-prestart-rubric"
    snapshot.pop("snapshotDigest")
    snapshot["snapshotDigest"] = compute_ai_policy_snapshot_digest(snapshot)

    validated = validate_ai_policy_snapshot_contract(snapshot)

    assert validated["promptPackVersion"] == "legacy-pack"
    assert validated["agents"]["prestart"]["promptVersion"] == "legacy-prestart"
    assert validated["agents"]["prestart"]["rubricVersion"] == "legacy-prestart-rubric"


@pytest.mark.parametrize(
    ("mutator", "error_code"),
    [
        (
            lambda snapshot: snapshot["agents"].pop("demoPresentationReviewer"),
            "scenario_version_ai_policy_snapshot_agent_contract_mismatch",
        ),
        (
            lambda snapshot: snapshot["agents"].update(
                {
                    "codespace": {
                        "key": "codespace",
                        "promptVersion": "legacy",
                        "rubricVersion": "legacy",
                        "runtime": {
                            "runtimeMode": "test",
                            "provider": "openai",
                            "model": "gpt-4.1",
                            "timeoutSeconds": 1,
                            "maxRetries": 0,
                        },
                        "policyFileName": "legacy.md",
                        "policySha256": "legacy",
                        "schemaFileName": "legacy.json",
                        "schemaSha256": "legacy",
                        "instructionsSha256": "legacy",
                        "rubricSha256": "legacy",
                        "resolvedInstructionsMd": "legacy",
                        "resolvedRubricMd": "legacy",
                    }
                }
            ),
            "scenario_version_ai_policy_snapshot_agent_contract_mismatch",
        ),
        (
            lambda snapshot: snapshot["agents"]["prestart"].pop("runtime"),
            "scenario_version_ai_policy_snapshot_runtime_missing",
        ),
        (
            lambda snapshot: snapshot["agents"]["prestart"].pop("resolvedRubricMd"),
            "scenario_version_ai_policy_snapshot_resolvedRubricMd_missing",
        ),
        (
            lambda snapshot: snapshot["agents"]["prestart"].pop("rubricVersion"),
            "scenario_version_ai_policy_snapshot_rubricVersion_missing",
        ),
    ],
)
def test_validate_ai_policy_snapshot_contract_rejects_malformed_stored_snapshot(
    mutator,
    error_code,
):
    snapshot = build_ai_policy_snapshot(trial=_trial())
    mutator(snapshot)

    with pytest.raises(AIPolicySnapshotError, match=error_code):
        validate_ai_policy_snapshot_contract(snapshot)


def test_validate_ai_policy_snapshot_contract_rejects_digest_mismatch():
    snapshot = build_ai_policy_snapshot(trial=_trial())
    snapshot["agents"]["prestart"]["runtime"]["provider"] = "__mutated-provider__"

    with pytest.raises(
        AIPolicySnapshotError,
        match="scenario_version_ai_policy_snapshot_digest_mismatch",
    ):
        validate_ai_policy_snapshot_contract(snapshot)


def test_compute_ai_policy_snapshot_basis_fingerprint_is_fixed_width_and_ignores_digest():
    snapshot = build_ai_policy_snapshot(trial=_trial())
    snapshot["snapshotDigest"] = "y" * 256

    fingerprint = compute_ai_policy_snapshot_basis_fingerprint(snapshot)

    assert len(fingerprint) == 64
    assert fingerprint != snapshot["snapshotDigest"]
