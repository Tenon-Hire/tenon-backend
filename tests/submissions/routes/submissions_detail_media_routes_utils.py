from __future__ import annotations

from fastapi import HTTPException

from app.integrations.storage_media.integrations_storage_media_storage_media_base_client import (
    StorageMediaError,
)
from app.media.repositories import recordings as recordings_repo
from app.media.repositories import transcripts as transcripts_repo
from app.media.repositories.recordings.media_repositories_recordings_media_recordings_core_model import (
    RECORDING_ASSET_STATUS_DELETED,
    RECORDING_ASSET_STATUS_UPLOADED,
)
from app.media.repositories.transcripts.media_repositories_transcripts_media_transcripts_core_model import (
    TRANSCRIPT_STATUS_READY,
)
from app.shared.utils.shared_utils_errors_utils import MEDIA_STORAGE_UNAVAILABLE
from app.submissions.routes.submissions_routes import (
    submissions_routes_submissions_routes_submissions_routes_detail_media_routes as detail_route,
)
from app.submissions.routes.submissions_routes import (
    submissions_routes_submissions_routes_submissions_routes_detail_routes as detail_submission_route,
)
from tests.shared.factories import (
    create_candidate_session,
    create_company,
    create_submission,
    create_talent_partner,
    create_trial,
)

# Keep tests patching `detail_route.get_storage_media_provider` while invoking
# `detail_route.get_submission_detail_route` after route/helper split.
if not hasattr(detail_route, "get_submission_detail_route"):
    detail_route.get_submission_detail_route = (
        detail_submission_route.get_submission_detail_route
    )


def _handoff_task(tasks):
    return next(task for task in tasks if task.type == "handoff")


__all__ = [name for name in globals() if not name.startswith("__")]
