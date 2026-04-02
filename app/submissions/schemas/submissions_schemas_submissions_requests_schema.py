"""Application module for submissions schemas submissions requests schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.shared.types.shared_types_base_model import APIModel
from app.shared.types.shared_types_progress_model import ProgressSummary


class SubmissionCreateRequest(BaseModel):
    """Represent submission create request data and behavior."""

    contentText: str | None = Field(default=None)
    reflection: Any | None = Field(default=None)
    branch: str | None = Field(default=None)
    workflowInputs: dict[str, Any] | None = Field(default=None)


class RunTestsRequest(BaseModel):
    """Represent run tests request data and behavior."""

    workflowInputs: dict[str, Any] | None = Field(default=None)
    branch: str | None = Field(default=None)


class RunTestsResponse(APIModel):
    """Represent run tests response data and behavior."""

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
    """Represent codespace init request data and behavior."""

    githubUsername: str


class CodespaceInitResponse(APIModel):
    """Represent codespace init response data and behavior."""

    repoFullName: str
    codespaceUrl: str
    codespaceState: str | None = None
    defaultBranch: str | None = None
    baseTemplateSha: str | None = None
    precommitSha: str | None = None
    workspaceId: str


class CodespaceStatusResponse(APIModel):
    """Represent codespace status response data and behavior."""

    repoFullName: str
    codespaceUrl: str | None = None
    codespaceState: str | None = None
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


class SubmissionCreateResponse(APIModel):
    """Represent submission create response data and behavior."""

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
