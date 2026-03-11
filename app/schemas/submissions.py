from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domains.common.base import APIModel
from app.domains.common.progress import ProgressSummary


class SubmissionCreateRequest(BaseModel):
    """Schema for creating a submission."""

    contentText: str | None = Field(default=None)
    reflection: Any | None = Field(default=None)
    branch: str | None = Field(default=None)
    workflowInputs: dict[str, Any] | None = Field(default=None)
    # Code tasks are GitHub-native; code payload is no longer accepted.


class RunTestsRequest(BaseModel):
    """Schema for executing GitHub Actions tests."""

    workflowInputs: dict[str, Any] | None = Field(default=None)
    branch: str | None = Field(default=None)


class RunTestsResponse(APIModel):
    """Schema for Actions run response."""

    status: str
    passed: int | None = None
    failed: int | None = None
    total: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    timeout: bool | None = None
    runId: int | None = None
    conclusion: str | None = None
    workflowUrl: str | None = None
    commitSha: str | None = None
    pollAfterMs: int | None = None


class CodespaceInitRequest(BaseModel):
    """Request to initialize a Codespace workspace."""

    githubUsername: str


class CodespaceInitResponse(APIModel):
    """Response payload for Codespace init."""

    repoFullName: str
    repoUrl: str
    codespaceUrl: str
    defaultBranch: str | None = None
    baseTemplateSha: str | None = None
    precommitSha: str | None = None
    workspaceId: str


class CodespaceStatusResponse(APIModel):
    """Current status for a workspace repo."""

    repoFullName: str
    repoUrl: str
    codespaceUrl: str | None = None
    defaultBranch: str | None = None
    baseTemplateSha: str | None = None
    precommitSha: str | None = None
    latestCommitSha: str | None = None
    lastWorkflowRunId: str | None = None
    lastWorkflowConclusion: str | None = None
    lastTestSummary: dict[str, Any] | None = None
    workspaceId: str
    cutoffCommitSha: str | None = None
    cutoffAt: datetime | None = None


class HandoffUploadInitRequest(BaseModel):
    """Request payload for handoff video upload init."""

    contentType: str
    sizeBytes: int = Field(gt=0)
    filename: str | None = None


class HandoffUploadInitResponse(APIModel):
    """Response payload for handoff video upload init."""

    recordingId: str
    uploadUrl: str
    expiresInSeconds: int


class HandoffUploadCompleteRequest(BaseModel):
    """Request payload for handoff video upload completion."""

    recordingId: str


class HandoffUploadCompleteResponse(APIModel):
    """Response payload for handoff video upload completion."""

    recordingId: str
    status: str


class HandoffStatusRecordingOut(APIModel):
    """Current recording state for Day 4 handoff."""

    recordingId: str
    status: str


class HandoffStatusTranscriptOut(APIModel):
    """Current transcript processing state for Day 4 handoff."""

    status: str
    progress: int | None = None


class HandoffStatusResponse(APIModel):
    """Polling response for Day 4 handoff processing."""

    recording: HandoffStatusRecordingOut | None = None
    transcript: HandoffStatusTranscriptOut | None = None


class SubmissionCreateResponse(APIModel):
    """Schema for submission creation response."""

    submissionId: int
    taskId: int
    candidateSessionId: int
    submittedAt: datetime
    commitSha: str | None = None
    cutoffCommitSha: str | None = None
    cutoffAt: datetime | None = None
    evalBasisRef: str | None = None
    checkpointSha: str | None = None
    finalSha: str | None = None
    progress: ProgressSummary
    isComplete: bool


class RecruiterTaskMetaOut(APIModel):
    """Schema for recruiter task metadata output."""

    taskId: int
    dayIndex: int
    type: str
    title: str | None = None
    prompt: str | None = None


class RecruiterCodeArtifactOut(APIModel):
    """Schema for recruiter code artifact output."""

    repoPath: str | None = None
    repoFullName: str | None = None
    repoUrl: str | None = None


class RecruiterTestResultsOut(APIModel):
    """Schema for recruiter test results output."""

    status: str | None = None
    passed: int | None = None
    failed: int | None = None
    total: int | None = None
    runId: int | str | None = None
    runStatus: str | None = None
    conclusion: str | None = None
    timeout: bool | None = None
    stdout: str | None = None
    stderr: str | None = None
    summary: dict[str, object] | None = None
    stdoutTruncated: bool | None = None
    stderrTruncated: bool | None = None
    artifactName: str | None = None
    artifactPresent: bool | None = None
    artifactErrorCode: str | None = None
    output: dict[str, object] | str | None = None
    lastRunAt: datetime | None = None
    workflowRunId: str | None = None
    commitSha: str | None = None
    workflowUrl: str | None = None
    commitUrl: str | None = None


class RecruiterRecordingAssetOut(APIModel):
    """Schema for recruiter-facing recording metadata."""

    recordingId: str
    contentType: str
    bytes: int
    status: str
    createdAt: datetime
    downloadUrl: str | None = None


class RecruiterTranscriptOut(APIModel):
    """Schema for recruiter-facing transcript metadata."""

    status: str
    modelName: str | None = None
    text: str | None = None
    segmentsJson: list[dict[str, Any]] | None = None
    segments: list[dict[str, Any]] | None = None


class RecruiterHandoffOut(APIModel):
    """Schema for recruiter-facing handoff payload."""

    recordingId: str | None = None
    downloadUrl: str | None = None
    transcript: RecruiterTranscriptOut | None = None


class RecruiterSubmissionDetailOut(APIModel):
    """Schema for recruiter submission details output."""

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
    """Schema for recruiter submission list item output."""

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
    """Schema for recruiter submission list output."""

    items: list[RecruiterSubmissionListItemOut]
    # Extend here if pagination is added later; keep per-item fields on the list item.
