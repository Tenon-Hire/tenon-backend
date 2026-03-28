from __future__ import annotations

import pytest

from app.submissions.repositories.precommit_bundles import repository as precommit_repo
from app.submissions.repositories.precommit_bundles.submissions_repositories_precommit_bundles_submissions_precommit_bundles_core_model import (
    PRECOMMIT_BUNDLE_STATUS_DISABLED,
    PRECOMMIT_BUNDLE_STATUS_READY,
)
from tests.submissions.repositories.precommit_bundles.submissions_precommit_bundles_repository_test_utils import (
    patch_body,
    seed_bundle_context,
)


@pytest.mark.asyncio
async def test_create_and_lookup_precommit_bundle(async_session):
    sim, scenario_version_id = await seed_bundle_context(
        async_session, email="bundle-repo@test.com"
    )
    bundle = await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=patch_body("README.md", "# Scenario baseline\n"),
        base_template_sha="base-sha-123",
    )
    by_key = await precommit_repo.get_by_scenario_and_template(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
    )
    assert by_key is not None and by_key.id == bundle.id
    assert by_key.base_template_sha == "base-sha-123"
    assert by_key.content_sha256 == precommit_repo.compute_content_sha256(
        patch_text=bundle.patch_text,
        storage_ref=None,
    )
    ready = await precommit_repo.get_ready_by_scenario_and_template(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
    )
    assert ready is not None and ready.id == bundle.id


@pytest.mark.asyncio
async def test_create_bundle_rejects_oversized_patch(async_session):
    sim, scenario_version_id = await seed_bundle_context(
        async_session, email="bundle-size@test.com"
    )
    with pytest.raises(ValueError):
        await precommit_repo.create_bundle(
            async_session,
            scenario_version_id=scenario_version_id,
            template_key=sim.template_key,
            status=PRECOMMIT_BUNDLE_STATUS_READY,
            patch_text="x" * (precommit_repo.MAX_PATCH_TEXT_BYTES + 1),
        )


@pytest.mark.asyncio
async def test_get_ready_by_scenario_and_template_filters_non_ready(async_session):
    sim, scenario_version_id = await seed_bundle_context(
        async_session, email="bundle-ready@test.com"
    )
    await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_DISABLED,
        patch_text=patch_body("README.md", "x"),
    )
    ready = await precommit_repo.get_ready_by_scenario_and_template(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
    )
    assert ready is None


@pytest.mark.asyncio
@pytest.mark.parametrize("commit", [True, False])
async def test_set_status_covers_commit_and_flush_branches(async_session, commit: bool):
    sim, scenario_version_id = await seed_bundle_context(
        async_session, email="bundle-set-status@test.com"
    )
    bundle = await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=patch_body("README.md", "status branch"),
    )

    updated = await precommit_repo.set_status(
        async_session,
        bundle=bundle,
        status=PRECOMMIT_BUNDLE_STATUS_DISABLED,
        commit=commit,
    )

    assert updated.id == bundle.id
    assert updated.status == PRECOMMIT_BUNDLE_STATUS_DISABLED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("applied_commit_sha", "expected", "commit"),
    [
        ("  deadbeef  ", "deadbeef", True),
        ("   ", None, False),
    ],
)
async def test_set_applied_commit_sha_covers_commit_and_flush_branches(
    async_session,
    applied_commit_sha: str,
    expected: str | None,
    commit: bool,
):
    sim, scenario_version_id = await seed_bundle_context(
        async_session, email="bundle-set-sha@test.com"
    )
    bundle = await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=patch_body("README.md", "sha branch"),
    )

    updated = await precommit_repo.set_applied_commit_sha(
        async_session,
        bundle=bundle,
        applied_commit_sha=applied_commit_sha,
        commit=commit,
    )

    assert updated.id == bundle.id
    assert updated.applied_commit_sha == expected
