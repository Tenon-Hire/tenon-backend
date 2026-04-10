from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.submissions.repositories import winoe_report_repository
from tests.shared.factories import (
    create_candidate_session,
    create_talent_partner,
    create_trial,
)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


@pytest.mark.asyncio
@pytest.mark.parametrize("commit", [True, False])
async def test_upsert_marker_create_branch(async_session, commit: bool):
    talent_partner = await create_talent_partner(
        async_session, email="winoe-report-create@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(async_session, trial=trial)
    generated_at = datetime(2026, 3, 20, 12, 0, tzinfo=UTC)

    marker = await winoe_report_repository.upsert_marker(
        async_session,
        candidate_session_id=candidate_session.id,
        generated_at=generated_at,
        commit=commit,
    )

    assert marker.id is not None
    assert marker.candidate_session_id == candidate_session.id
    assert _as_utc(marker.generated_at) == generated_at
    loaded = await winoe_report_repository.get_by_candidate_session_id(
        async_session, candidate_session_id=candidate_session.id
    )
    assert loaded is not None
    assert loaded.id == marker.id


@pytest.mark.asyncio
@pytest.mark.parametrize("commit", [True, False])
async def test_upsert_marker_update_branch(async_session, commit: bool):
    talent_partner = await create_talent_partner(
        async_session, email="winoe-report-update@test.com"
    )
    trial, _tasks = await create_trial(async_session, created_by=talent_partner)
    candidate_session = await create_candidate_session(async_session, trial=trial)
    first_time = datetime(2026, 3, 20, 10, 0, tzinfo=UTC)
    updated_time = datetime(2026, 3, 20, 13, 30, tzinfo=UTC)

    created = await winoe_report_repository.upsert_marker(
        async_session,
        candidate_session_id=candidate_session.id,
        generated_at=first_time,
    )
    updated = await winoe_report_repository.upsert_marker(
        async_session,
        candidate_session_id=candidate_session.id,
        generated_at=updated_time,
        commit=commit,
    )

    assert updated.id == created.id
    assert _as_utc(updated.generated_at) == updated_time
    loaded = await winoe_report_repository.get_by_candidate_session_id(
        async_session, candidate_session_id=candidate_session.id
    )
    assert loaded is not None
    assert loaded.id == created.id
    assert _as_utc(loaded.generated_at) == updated_time
