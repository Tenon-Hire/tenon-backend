from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_submission_progress_reraises_unrelated_type_error(monkeypatch):
    async def _raise_type_error(*_args, **_kwargs):
        raise TypeError("boom")

    monkeypatch.setattr(
        submission_progress.cs_service,
        "progress_snapshot",
        _raise_type_error,
    )

    with pytest.raises(TypeError):
        await submission_progress.progress_after_submission(
            object(),
            SimpleNamespace(status="in_progress", completed_at=None),
            now=datetime.now(UTC),
            tasks=[],
        )
