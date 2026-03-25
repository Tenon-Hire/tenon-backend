from __future__ import annotations

from datetime import datetime
from typing import Any

from app.shared.types.shared_types_base_model import APIModel


class RecruiterTaskMetaOut(APIModel):
    taskId: int
    dayIndex: int
    type: str
    title: str | None = None
    prompt: str | None = None


class RecruiterCodeArtifactOut(APIModel):
    repoPath: str | None = None
    repoFullName: str | None = None
    repoUrl: str | None = None


class RecruiterTestResultsOut(APIModel):
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
    recordingId: str
    contentType: str
    bytes: int
    status: str
    createdAt: datetime
    downloadUrl: str | None = None


class RecruiterTranscriptOut(APIModel):
    status: str
    modelName: str | None = None
    text: str | None = None
    segmentsJson: list[dict[str, Any]] | None = None
    segments: list[dict[str, Any]] | None = None
