from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_day_close_enforcement_utils import *


@pytest.mark.asyncio
async def test_day_close_enforcement_resolve_default_branch_variants():
    class Client:
        async def get_repo(self, repo_full_name: str):
            if repo_full_name.endswith("blank"):
                return {"default_branch": "   "}
            return {"default_branch": "develop"}

    client = Client()
    assert (
        await enforcement_handler._resolve_default_branch(
            client,
            repo_full_name="org/repo",
            workspace_default_branch=" feature ",
        )
        == "feature"
    )
    assert (
        await enforcement_handler._resolve_default_branch(
            client,
            repo_full_name="org/repo",
            workspace_default_branch=None,
        )
        == "develop"
    )
    assert (
        await enforcement_handler._resolve_default_branch(
            client,
            repo_full_name="org/repo-blank",
            workspace_default_branch="",
        )
        == "main"
    )
