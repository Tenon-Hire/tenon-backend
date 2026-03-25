from __future__ import annotations

import pytest

from tests.candidates.routes.candidates_submissions_routes_utils import *


@pytest.mark.asyncio
async def test_get_run_result_missing_headers(async_session):
    with pytest.raises(HTTPException) as excinfo:
        await candidate_session_from_headers(
            principal=_principal(), x_candidate_session_id=None, db=async_session
        )
    assert excinfo.value.status_code == 401
