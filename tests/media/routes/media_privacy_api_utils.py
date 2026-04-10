from __future__ import annotations

# helper import baseline for restructure-compat
from sqlalchemy import select

from app.integrations.storage_media import (
    FakeStorageMediaProvider,
    get_storage_media_provider,
)
from app.media.repositories.recordings import repository as recordings_repo
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_STATUS_UPLOADED,
)
from app.shared.database.shared_database_models_model import (
    CandidateSession,
    RecordingAsset,
    Submission,
)
from tests.shared.factories import (
    create_candidate_session,
    create_company,
    create_talent_partner,
    create_trial,
)


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


def _fake_storage_provider() -> FakeStorageMediaProvider:
    provider = get_storage_media_provider()
    assert isinstance(provider, FakeStorageMediaProvider)
    return provider


async def _seed_uploaded_recording(
    async_session,
    *,
    candidate_session,
    task_id: int,
    filename: str,
) -> RecordingAsset:
    return await recordings_repo.create_recording_asset(
        async_session,
        candidate_session_id=candidate_session.id,
        task_id=task_id,
        storage_key=(
            f"candidate-sessions/{candidate_session.id}/tasks/{task_id}/"
            f"recordings/{filename}"
        ),
        content_type="video/mp4",
        bytes_count=1024,
        status=RECORDING_ASSET_STATUS_UPLOADED,
        commit=True,
    )


async def _latest_recording(async_session, *, candidate_session_id: int, task_id: int):
    query = (
        select(RecordingAsset)
        .where(
            RecordingAsset.candidate_session_id == candidate_session_id,
            RecordingAsset.task_id == task_id,
        )
        .order_by(RecordingAsset.id.desc())
    )
    return (await async_session.execute(query)).scalars().first()


async def _submission_for_task(
    async_session, *, candidate_session_id: int, task_id: int
):
    query = select(Submission).where(
        Submission.candidate_session_id == candidate_session_id,
        Submission.task_id == task_id,
    )
    return (await async_session.execute(query)).scalars().first()


__all__ = [name for name in globals() if not name.startswith("__")]
