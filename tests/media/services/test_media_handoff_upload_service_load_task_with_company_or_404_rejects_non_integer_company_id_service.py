from __future__ import annotations

import pytest

from tests.media.services.media_handoff_upload_service_utils import *


@pytest.mark.asyncio
async def test_load_task_with_company_or_404_rejects_non_integer_company_id():
    class _Result:
        def one_or_none(self):
            return SimpleNamespace(id=1), "oops"

    class _FakeDB:
        async def execute(self, _stmt):
            return _Result()

    with pytest.raises(HTTPException) as exc_info:
        await _load_task_with_company_or_404(_FakeDB(), task_id=1)
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Trial metadata unavailable"
