from __future__ import annotations

import pytest

from tests.shared.jobs.handlers.shared_jobs_handlers_workspace_cleanup_utils import *


@pytest.mark.asyncio
async def test_workspace_cleanup_invalid_payload_is_skipped():
    result = await cleanup_handler.handle_workspace_cleanup({"companyId": "invalid"})
    assert result == {"status": "skipped_invalid_payload", "companyId": None}
