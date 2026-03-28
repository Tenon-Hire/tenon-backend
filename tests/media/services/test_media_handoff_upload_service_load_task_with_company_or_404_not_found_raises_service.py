from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_load_task_with_company_or_404_not_found_raises():
    class _Result:
        def one_or_none(self):
            return None

    class _FakeDB:
        async def execute(self, _stmt):
            return _Result()

    with pytest.raises(HTTPException) as exc_info:
        await _load_task_with_company_or_404(_FakeDB(), task_id=999)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Task not found"
