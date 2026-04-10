from __future__ import annotations

import pytest

from tests.submissions.services.precommit_bundle_runtime.submissions_precommit_bundle_runtime_test_utils import *


@pytest.mark.asyncio
async def test_apply_precommit_bundle_success(async_session):
    talent_partner = await create_talent_partner(
        async_session, email="bundle-apply@test.com"
    )
    sim, tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(
        async_session,
        trial=sim,
        status="in_progress",
    )
    scenario_version_id = candidate_session.scenario_version_id
    assert scenario_version_id is not None

    bundle = await precommit_repo.create_bundle(
        async_session,
        scenario_version_id=scenario_version_id,
        template_key=sim.template_key,
        status=PRECOMMIT_BUNDLE_STATUS_READY,
        patch_text=json.dumps(
            {
                "files": [
                    {"path": "README.md", "content": "# Baseline\n"},
                    {
                        "path": "scripts/setup.sh",
                        "content": "#!/usr/bin/env bash\necho setup\n",
                        "executable": True,
                    },
                ]
            }
        ),
        base_template_sha="base-sha-123",
    )
    github_client = StubGithubClient()

    result = await apply_precommit_bundle_if_available(
        async_session,
        github_client=github_client,
        candidate_session=candidate_session,
        task=tasks[1],
        repo_full_name="org/workspace-repo",
        default_branch="main",
        base_template_sha="base-sha-123",
        existing_precommit_sha=None,
    )

    assert result.state == "applied"
    assert result.precommit_sha == "new-commit-sha"
    assert result.bundle_id == bundle.id
    assert len(github_client.created_blobs) == 2
    assert len(github_client.created_trees) == 1
    assert len(github_client.created_commits) == 1
    assert github_client.updated_refs == [("heads/main", "new-commit-sha", False)]
    commit_message = github_client.created_commits[0][0]
    assert (
        build_precommit_commit_marker(bundle.id, bundle.content_sha256)
        in commit_message
    )
