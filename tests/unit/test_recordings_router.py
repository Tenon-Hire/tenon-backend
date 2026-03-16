from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routers import recordings as recordings_router
from app.core.auth.principal import Principal


def _principal() -> Principal:
    return Principal(
        sub="candidate-test",
        email="candidate@test.com",
        name="candidate",
        roles=[],
        permissions=["candidate:access"],
        claims={"email_verified": True},
    )


@pytest.mark.asyncio
async def test_delete_recording_route_returns_deleted_status(monkeypatch):
    async def _get_by_id(db, recording_id: int):
        del db
        return SimpleNamespace(id=recording_id, candidate_session_id=9)

    async def _fetch_owned_session(db, session_id: int, principal, *, now):
        del db, principal, now
        return SimpleNamespace(id=session_id)

    async def _delete_recording_asset(
        db,
        *,
        recording_id: int,
        candidate_session,
    ):
        del db
        assert recording_id == 42
        assert candidate_session.id == 9
        return None

    monkeypatch.setattr(recordings_router.recordings_repo, "get_by_id", _get_by_id)
    monkeypatch.setattr(
        recordings_router.cs_service,
        "fetch_owned_session",
        _fetch_owned_session,
    )
    monkeypatch.setattr(
        recordings_router,
        "delete_recording_asset",
        _delete_recording_asset,
    )

    result = await recordings_router.delete_recording_route(
        recording_id="rec_42",
        principal=_principal(),
        db=None,
    )
    assert result.status == "deleted"


@pytest.mark.asyncio
async def test_delete_recording_route_rejects_invalid_recording_id():
    with pytest.raises(HTTPException) as exc_info:
        await recordings_router.delete_recording_route(
            recording_id="bad-id",
            principal=_principal(),
            db=None,
        )

    assert exc_info.value.status_code == 422
    assert "recordingId" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_recording_route_returns_404_for_missing_recording(monkeypatch):
    async def _get_by_id(db, recording_id: int):
        del db, recording_id
        return None

    monkeypatch.setattr(recordings_router.recordings_repo, "get_by_id", _get_by_id)

    with pytest.raises(HTTPException) as exc_info:
        await recordings_router.delete_recording_route(
            recording_id="rec_42",
            principal=_principal(),
            db=None,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Recording asset not found"


@pytest.mark.asyncio
async def test_delete_recording_route_propagates_forbidden_session_access(monkeypatch):
    async def _get_by_id(db, recording_id: int):
        del db
        return SimpleNamespace(id=recording_id, candidate_session_id=9)

    async def _fetch_owned_session(db, session_id: int, principal, *, now):
        del db, session_id, principal, now
        raise HTTPException(status_code=403, detail="forbidden")

    monkeypatch.setattr(recordings_router.recordings_repo, "get_by_id", _get_by_id)
    monkeypatch.setattr(
        recordings_router.cs_service,
        "fetch_owned_session",
        _fetch_owned_session,
    )

    with pytest.raises(HTTPException) as exc_info:
        await recordings_router.delete_recording_route(
            recording_id="rec_42",
            principal=_principal(),
            db=None,
        )

    assert exc_info.value.status_code == 403
