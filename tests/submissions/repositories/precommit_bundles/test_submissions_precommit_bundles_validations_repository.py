from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.submissions.repositories.precommit_bundles import repository as precommit_repo
from app.submissions.repositories.precommit_bundles.submissions_repositories_precommit_bundles_submissions_precommit_bundles_core_model import (
    PRECOMMIT_BUNDLE_STATUS_DISABLED,
    PRECOMMIT_BUNDLE_STATUS_DRAFT,
    PRECOMMIT_BUNDLE_STATUS_READY,
)
from tests.submissions.repositories.precommit_bundles.submissions_precommit_bundles_repository_test_utils import (
    patch_body,
    seed_bundle_context,
)


@pytest.mark.asyncio
async def test_create_bundle_and_status_transitions_with_storage_ref(async_session):
    sim, scenario_version_id = await seed_bundle_context(
        async_session, email="bundle-status@test.com"
    )
    checksum = precommit_repo.compute_content_sha256(storage_ref="ref:bundle@abc")
    bundle = await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_DRAFT,
        storage_ref="ref:bundle@abc",
        content_sha256=checksum,
        commit=False,
    )
    assert bundle.content_sha256 == checksum
    updated = await precommit_repo.set_status(
        async_session,
        bundle=bundle,
        status=PRECOMMIT_BUNDLE_STATUS_DISABLED,
        commit=False,
    )
    assert updated.status == PRECOMMIT_BUNDLE_STATUS_DISABLED
    updated = await precommit_repo.set_applied_commit_sha(
        async_session,
        bundle=bundle,
        applied_commit_sha="  commit-sha-123  ",
        commit=False,
    )
    assert updated.applied_commit_sha == "commit-sha-123"
    updated = await precommit_repo.set_applied_commit_sha(
        async_session,
        bundle=bundle,
        applied_commit_sha="",
        commit=False,
    )
    assert updated.applied_commit_sha is None


@pytest.mark.asyncio
async def test_precommit_bundle_unique_constraint_enforced(async_session):
    sim, scenario_version_id = await seed_bundle_context(
        async_session, email="bundle-unique@test.com"
    )
    await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=patch_body("README.md", "x"),
    )
    with pytest.raises(IntegrityError):
        await precommit_repo.create_bundle(
            async_session,
            scenario_version_id=scenario_version_id,
            template_key=sim.template_key,
            status=PRECOMMIT_BUNDLE_STATUS_DISABLED,
            patch_text=patch_body("README-2.md", "y"),
        )
    await async_session.rollback()


@pytest.mark.asyncio
async def test_precommit_bundle_repository_validation_errors(async_session):
    sim, scenario_version_id = await seed_bundle_context(
        async_session, email="bundle-errors@test.com"
    )
    with pytest.raises(ValueError):
        precommit_repo.compute_content_sha256()
    with pytest.raises(ValueError):
        await precommit_repo.create_bundle(
            async_session,
            scenario_version_id=scenario_version_id,
            template_key=" ",
            status=PRECOMMIT_BUNDLE_STATUS_READY,
            patch_text=patch_body("README.md", "x"),
        )
    with pytest.raises(ValueError):
        await precommit_repo.create_bundle(
            async_session,
            scenario_version_id=scenario_version_id,
            template_key=sim.template_key,
            status="bad-status",
            patch_text=patch_body("README.md", "x"),
        )
    bundle = await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=patch_body("README.md", "x"),
    )
    with pytest.raises(ValueError):
        await precommit_repo.set_status(
            async_session, bundle=bundle, status="not-valid"
        )
