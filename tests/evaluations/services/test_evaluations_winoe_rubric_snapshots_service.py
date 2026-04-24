from __future__ import annotations

from hashlib import sha256

import pytest
from sqlalchemy import select

from app.ai import (
    compute_ai_policy_snapshot_digest,
    validate_ai_policy_snapshot_contract,
)
from app.evaluations.repositories import (
    RUBRIC_SNAPSHOT_SCOPE_COMPANY,
    RUBRIC_SNAPSHOT_SCOPE_WINOE,
    list_rubric_snapshots_for_scenario_version,
)
from app.evaluations.services.evaluations_services_evaluations_winoe_rubric_snapshots_service import (
    WINOE_RUBRIC_REGISTRY,
    RubricSnapshotMaterializationError,
    get_rubric_snapshots_for_scenario_version,
    materialize_scenario_version_rubric_snapshots,
)
from app.shared.database.shared_database_models_model import ScenarioVersion
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _rubric_snapshot_ids(snapshot_bundle: dict[str, object]) -> list[int]:
    return [int(item["snapshotId"]) for item in snapshot_bundle["rubricSnapshots"]]


@pytest.mark.asyncio
async def test_materialize_winoe_rubric_snapshots_persists_and_is_idempotent(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="rubric-snapshots@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    scenario_version = await async_session.scalar(
        select(ScenarioVersion).where(
            ScenarioVersion.id == trial.active_scenario_version_id
        )
    )
    assert scenario_version is not None

    first = await materialize_scenario_version_rubric_snapshots(
        async_session, scenario_version=scenario_version, trial=trial
    )
    second = await materialize_scenario_version_rubric_snapshots(
        async_session, scenario_version=scenario_version, trial=trial
    )
    snapshots = await list_rubric_snapshots_for_scenario_version(
        async_session, scenario_version_id=scenario_version.id
    )

    assert len(snapshots) == len(WINOE_RUBRIC_REGISTRY)
    assert _rubric_snapshot_ids(first) == _rubric_snapshot_ids(second)

    first_snapshot = next(
        snapshot
        for snapshot in snapshots
        if snapshot.scope == RUBRIC_SNAPSHOT_SCOPE_WINOE
        and snapshot.rubric_key == "designDocReviewer"
    )
    assert first_snapshot.rubric_kind == "day_1_design_doc"
    assert first_snapshot.source_path == "app/ai/prompt_assets/v1/winoe-day-1-rubric.md"
    assert (
        first_snapshot.content_hash
        == sha256(first_snapshot.content_md.encode("utf-8")).hexdigest()
    )
    assert (
        first["effectiveAiPolicySnapshotJson"]["agents"]["designDocReviewer"][
            "resolvedRubricMd"
        ]
        == first_snapshot.content_md
    )
    assert first["effectiveAiPolicySnapshotJson"][
        "snapshotDigest"
    ] == compute_ai_policy_snapshot_digest(first["effectiveAiPolicySnapshotJson"])
    validate_ai_policy_snapshot_contract(
        first["effectiveAiPolicySnapshotJson"],
        scenario_version_id=scenario_version.id,
    )
    assert first["rubricSnapshots"][0]["snapshotId"] == first_snapshot.id


@pytest.mark.asyncio
async def test_company_rubric_snapshot_is_immutable_and_becomes_effective(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="company-rubric@test.com"
    )
    trial, _tasks = await create_trial(
        async_session,
        created_by=talent_partner,
        company_rubric_json={
            "designDocReviewer": {
                "content": "# Company design rubric\n\nPrefer evidence trails.",
                "versionId": "company-design-v1",
            }
        },
    )
    scenario_version = await async_session.scalar(
        select(ScenarioVersion).where(
            ScenarioVersion.id == trial.active_scenario_version_id
        )
    )
    assert scenario_version is not None

    first = await materialize_scenario_version_rubric_snapshots(
        async_session, scenario_version=scenario_version, trial=trial
    )
    company_snapshot = next(
        snapshot
        for snapshot in first["snapshots"]
        if snapshot.scope == RUBRIC_SNAPSHOT_SCOPE_COMPANY
        and snapshot.rubric_key == "designDocReviewer"
    )
    assert company_snapshot.rubric_version == "company-design-v1"
    assert company_snapshot.content_md.startswith("# Company design rubric")
    assert (
        first["effectiveAiPolicySnapshotJson"]["agents"]["designDocReviewer"][
            "resolvedRubricMd"
        ]
        == company_snapshot.content_md
    )

    trial.company_rubric_json["designDocReviewer"] = {
        "content": "# Company design rubric\n\nPrefer different evidence.",
        "versionId": "company-design-v1",
    }

    second = await materialize_scenario_version_rubric_snapshots(
        async_session, scenario_version=scenario_version, trial=trial
    )
    company_snapshot_again = next(
        snapshot
        for snapshot in second["snapshots"]
        if snapshot.scope == RUBRIC_SNAPSHOT_SCOPE_COMPANY
        and snapshot.rubric_key == "designDocReviewer"
    )
    assert company_snapshot_again.id == company_snapshot.id
    assert company_snapshot_again.content_md == company_snapshot.content_md
    assert company_snapshot_again.rubric_version == company_snapshot.rubric_version
    assert (
        second["effectiveAiPolicySnapshotJson"]["agents"]["designDocReviewer"][
            "resolvedRubricMd"
        ]
        == company_snapshot.content_md
    )


@pytest.mark.asyncio
async def test_company_rubric_snapshot_ignores_unknown_key_and_rejects_blank_content(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="company-rubric-shape@test.com"
    )
    trial, _tasks = await create_trial(
        async_session,
        created_by=talent_partner,
        company_rubric_json={
            "unknownReviewer": {
                "content": "# Not used",
                "versionId": "ignored",
            },
            "designDocReviewer": {"content": "   ", "versionId": "blank"},
        },
    )
    scenario_version = await async_session.scalar(
        select(ScenarioVersion).where(
            ScenarioVersion.id == trial.active_scenario_version_id
        )
    )
    assert scenario_version is not None

    with pytest.raises(RubricSnapshotMaterializationError):
        await materialize_scenario_version_rubric_snapshots(
            async_session, scenario_version=scenario_version, trial=trial
        )


@pytest.mark.asyncio
async def test_rubric_snapshots_are_shared_across_candidates_in_same_trial(
    async_session,
):
    talent_partner = await create_talent_partner(
        async_session, email="same-trial@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_a = await create_candidate_session(async_session, trial=trial)
    candidate_b = await create_candidate_session(
        async_session,
        trial=trial,
        invite_email="candidate-b@example.com",
    )

    assert candidate_a.scenario_version_id == candidate_b.scenario_version_id
    scenario_version = await async_session.scalar(
        select(ScenarioVersion).where(
            ScenarioVersion.id == candidate_a.scenario_version_id
        )
    )
    assert scenario_version is not None
    bundle = await get_rubric_snapshots_for_scenario_version(
        async_session, scenario_version=scenario_version, trial=trial
    )
    snapshot_ids = _rubric_snapshot_ids(bundle)
    assert snapshot_ids == sorted(snapshot_ids)
    assert bundle["scenarioVersionId"] == candidate_a.scenario_version_id
    assert bundle["trialId"] == trial.id
