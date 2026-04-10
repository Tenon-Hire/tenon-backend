"""Application module for submissions schemas submissions Talent Partner outputs schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.shared.types.shared_types_base_model import APIModel

from .submissions_schemas_submissions_talent_partner_base_schema import (
    TalentPartnerCodeArtifactOut,
    TalentPartnerRecordingAssetOut,
    TalentPartnerTaskMetaOut,
    TalentPartnerTestResultsOut,
    TalentPartnerTranscriptOut,
)


class TalentPartnerHandoffOut(APIModel):
    """Represent Talent Partner handoff out data and behavior."""

    recordingId: str | None = None
    downloadUrl: str | None = None
    transcript: TalentPartnerTranscriptOut | None = None


class TalentPartnerSubmissionDetailOut(APIModel):
    """Represent Talent Partner submission detail out data and behavior."""

    submissionId: int
    candidateSessionId: int
    task: TalentPartnerTaskMetaOut
    contentText: str | None = None
    contentJson: dict[str, Any] | None = None
    code: TalentPartnerCodeArtifactOut | None = None
    testResults: TalentPartnerTestResultsOut | None = None
    diffSummary: dict[str, object] | str | None = None
    submittedAt: datetime
    commitSha: str | None = None
    cutoffCommitSha: str | None = None
    cutoffAt: datetime | None = None
    evalBasisRef: str | None = None
    workflowUrl: str | None = None
    commitUrl: str | None = None
    diffUrl: str | None = None
    recording: TalentPartnerRecordingAssetOut | None = None
    transcript: TalentPartnerTranscriptOut | None = None
    handoff: TalentPartnerHandoffOut | None = None


class TalentPartnerSubmissionListItemOut(APIModel):
    """Represent Talent Partner submission list item out data and behavior."""

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
    testResults: TalentPartnerTestResultsOut | None = None


class TalentPartnerSubmissionListOut(APIModel):
    """Represent Talent Partner submission list out data and behavior."""

    items: list[TalentPartnerSubmissionListItemOut]
