"""Application module for submissions schemas submissions recruiter outputs schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.shared.types.shared_types_base_model import APIModel

from .submissions_schemas_submissions_recruiter_base_schema import (
    RecruiterCodeArtifactOut,
    RecruiterRecordingAssetOut,
    RecruiterTaskMetaOut,
    RecruiterTestResultsOut,
    RecruiterTranscriptOut,
)


class RecruiterHandoffOut(APIModel):
    """Represent recruiter handoff out data and behavior."""

    recordingId: str | None = None
    downloadUrl: str | None = None
    transcript: RecruiterTranscriptOut | None = None


class RecruiterSubmissionDetailOut(APIModel):
    """Represent recruiter submission detail out data and behavior."""

    submissionId: int
    candidateSessionId: int
    task: RecruiterTaskMetaOut
    contentText: str | None = None
    contentJson: dict[str, Any] | None = None
    code: RecruiterCodeArtifactOut | None = None
    testResults: RecruiterTestResultsOut | None = None
    diffSummary: dict[str, object] | str | None = None
    submittedAt: datetime
    commitSha: str | None = None
    cutoffCommitSha: str | None = None
    cutoffAt: datetime | None = None
    evalBasisRef: str | None = None
    workflowUrl: str | None = None
    commitUrl: str | None = None
    diffUrl: str | None = None
    recording: RecruiterRecordingAssetOut | None = None
    transcript: RecruiterTranscriptOut | None = None
    handoff: RecruiterHandoffOut | None = None


class RecruiterSubmissionListItemOut(APIModel):
    """Represent recruiter submission list item out data and behavior."""

    submissionId: int
    candidateSessionId: int
    taskId: int
    dayIndex: int
    type: str
    submittedAt: datetime
    repoFullName: str | None = None
    repoUrl: str | None = None
    workflowRunId: str | None = None
    commitSha: str | None = None
    cutoffCommitSha: str | None = None
    cutoffAt: datetime | None = None
    evalBasisRef: str | None = None
    workflowUrl: str | None = None
    commitUrl: str | None = None
    diffUrl: str | None = None
    diffSummary: dict[str, object] | str | None = None
    testResults: RecruiterTestResultsOut | None = None


class RecruiterSubmissionListOut(APIModel):
    """Represent recruiter submission list out data and behavior."""

    items: list[RecruiterSubmissionListItemOut]
