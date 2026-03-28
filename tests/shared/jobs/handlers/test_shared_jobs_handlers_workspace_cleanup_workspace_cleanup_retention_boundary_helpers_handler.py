from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_retention_boundary_helpers():
    anchor = datetime(2026, 3, 13, 12, 0, tzinfo=UTC)
    expires_0 = cleanup_handler._retention_expires_at(anchor, retention_days=0)
    expires_1 = cleanup_handler._retention_expires_at(anchor, retention_days=1)
    expires_7 = cleanup_handler._retention_expires_at(anchor, retention_days=7)

    assert cleanup_handler._retention_expired(now=anchor, expires_at=expires_0) is False
    assert (
        cleanup_handler._retention_expired(
            now=anchor + timedelta(seconds=1),
            expires_at=expires_0,
        )
        is True
    )
    assert (
        cleanup_handler._retention_expired(
            now=anchor + timedelta(days=1),
            expires_at=expires_1,
        )
        is False
    )
    assert (
        cleanup_handler._retention_expired(
            now=anchor + timedelta(days=1, seconds=1),
            expires_at=expires_1,
        )
        is True
    )
    assert (
        cleanup_handler._retention_expired(
            now=anchor + timedelta(days=7, seconds=1),
            expires_at=expires_7,
        )
        is True
    )
