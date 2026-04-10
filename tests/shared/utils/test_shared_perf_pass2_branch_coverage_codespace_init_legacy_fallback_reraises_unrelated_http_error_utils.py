from __future__ import annotations

import pytest

from tests.shared.utils.shared_perf_pass2_branch_coverage_utils import *


@pytest.mark.asyncio
async def test_codespace_init_legacy_fallback_reraises_unrelated_http_error(
    monkeypatch,
):
    async def _raise_not_found(*_args, **_kwargs):
        raise HTTPException(status_code=404, detail="Task not found")

    monkeypatch.setattr(
        codespace_init_use_case,
        "validate_codespace_request",
        _raise_not_found,
    )

    with pytest.raises(HTTPException) as excinfo:
        await _validate_codespace_request_with_legacy_fallback(
            object(),
            SimpleNamespace(id=1, trial_id=2),
            99,
        )
    assert excinfo.value.status_code == 404
