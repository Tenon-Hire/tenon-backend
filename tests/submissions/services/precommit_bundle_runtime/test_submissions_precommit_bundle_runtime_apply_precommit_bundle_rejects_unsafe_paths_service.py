from __future__ import annotations

import pytest

from tests.submissions.services.precommit_bundle_runtime.submissions_precommit_bundle_runtime_test_utils import *


@pytest.mark.asyncio
async def test_apply_precommit_bundle_rejects_unsafe_paths(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="bundle-unsafe@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
    )
    scenario_version_id = candidate_session.scenario_version_id
    assert scenario_version_id is not None

    await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=json.dumps(
            {"files": [{"path": "../secrets.env", "content": "SHOULD_NOT_APPLY=1\n"}]}
        ),
    )
    github_client = StubGithubClient()

    with pytest.raises(ApiError) as excinfo:
        await apply_precommit_bundle_if_available(
            async_session,
            github_client=github_client,
            candidate_session=candidate_session,
            task=tasks[1],
            repo_full_name="org/workspace-repo",
            default_branch="main",
            base_template_sha="base-sha-123",
            existing_precommit_sha=None,
        )

    assert excinfo.value.error_code == "PRECOMMIT_PATCH_UNSAFE_PATH"
