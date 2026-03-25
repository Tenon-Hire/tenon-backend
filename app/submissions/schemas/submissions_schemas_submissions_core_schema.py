from __future__ import annotations

from app.shared.types.shared_types_progress_model import ProgressSummary

from .submissions_schemas_submissions_handoff_schema import (
    HandoffStatusRecordingOut,
    HandoffStatusResponse,
    HandoffStatusTranscriptOut,
    HandoffStatusTranscriptSegmentOut,
    HandoffUploadCompleteRequest,
    HandoffUploadCompleteResponse,
    HandoffUploadInitRequest,
    HandoffUploadInitResponse,
)
from .submissions_schemas_submissions_recruiter_base_schema import (
    RecruiterCodeArtifactOut,
    RecruiterRecordingAssetOut,
    RecruiterTaskMetaOut,
    RecruiterTestResultsOut,
    RecruiterTranscriptOut,
)
from .submissions_schemas_submissions_recruiter_outputs_schema import (
    RecruiterHandoffOut,
    RecruiterSubmissionDetailOut,
    RecruiterSubmissionListItemOut,
    RecruiterSubmissionListOut,
)
from .submissions_schemas_submissions_requests_schema import (
    CodespaceInitRequest,
    CodespaceInitResponse,
    CodespaceStatusResponse,
    RunTestsRequest,
    RunTestsResponse,
    SubmissionCreateRequest,
    SubmissionCreateResponse,
)

__all__ = [
    "SubmissionCreateRequest",
    "RunTestsRequest",
    "RunTestsResponse",
    "CodespaceInitRequest",
    "CodespaceInitResponse",
    "CodespaceStatusResponse",
    "HandoffUploadInitRequest",
    "HandoffUploadInitResponse",
    "HandoffUploadCompleteRequest",
    "HandoffUploadCompleteResponse",
    "HandoffStatusRecordingOut",
    "HandoffStatusTranscriptSegmentOut",
    "HandoffStatusTranscriptOut",
    "HandoffStatusResponse",
    "SubmissionCreateResponse",
    "ProgressSummary",
    "RecruiterTaskMetaOut",
    "RecruiterCodeArtifactOut",
    "RecruiterTestResultsOut",
    "RecruiterRecordingAssetOut",
    "RecruiterTranscriptOut",
    "RecruiterHandoffOut",
    "RecruiterSubmissionDetailOut",
    "RecruiterSubmissionListItemOut",
    "RecruiterSubmissionListOut",
]
