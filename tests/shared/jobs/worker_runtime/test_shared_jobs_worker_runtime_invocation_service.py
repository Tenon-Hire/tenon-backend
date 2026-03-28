from __future__ import annotations

import pytest

from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_invocation_service import (
    invoke_handler,
)
from app.shared.jobs.worker_runtime.shared_jobs_worker_runtime_types_model import (
    PermanentJobError,
)


@pytest.mark.asyncio
async def test_invoke_handler_accepts_sync_dict_result() -> None:
    def _handler(payload_json: dict[str, int]) -> dict[str, int]:
        return {"x": payload_json["x"]}

    result = await invoke_handler(_handler, {"x": 7})
    assert result == {"x": 7}


@pytest.mark.asyncio
async def test_invoke_handler_awaits_async_result() -> None:
    async def _handler(payload_json: dict[str, int]) -> dict[str, int]:
        return {"x": payload_json["x"] + 1}

    result = await invoke_handler(_handler, {"x": 7})
    assert result == {"x": 8}


@pytest.mark.asyncio
async def test_invoke_handler_rejects_non_dict_result() -> None:
    def _handler(_: dict[str, int]) -> str:
        return "bad"

    with pytest.raises(
        PermanentJobError, match="job handler result must be a JSON object or null"
    ):
        await invoke_handler(_handler, {"x": 1})
