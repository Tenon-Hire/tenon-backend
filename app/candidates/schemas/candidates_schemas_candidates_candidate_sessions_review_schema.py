"""Application module for candidates schemas candidates candidate sessions review schema workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from app.candidates.schemas.candidates_schemas_candidates_candidate_sessions_windows_schema import (
    CandidateTrialSummary,
    DayWindow,
)
from app.shared.types.shared_types_base_model import APIModel
from app.shared.types.shared_types_types_model import CandidateSessionStatus
from app.submissions.schemas.submissions_schemas_submissions_talent_partner_base_schema import (
    TalentPartnerRecordingAssetOut,
    TalentPartnerTestResultsOut,
    TalentPartnerTranscriptOut,
)


class CandidateReviewMarkdownArtifact(APIModel):
    """Read-only markdown submission artifact for candidate review."""

    kind: Literal["markdown"]
    dayIndex: int
    taskId: int
    taskType: str
    title: str
    submittedAt: datetime
    markdown: str | None = None
    contentJson: dict[str, Any] | None = None


class CandidateReviewWorkspaceArtifact(APIModel):
    """Read-only workspace artifact summary for candidate review."""

    kind: Literal["workspace"]
    dayIndex: int
    taskId: int
    taskType: str
    title: str
    submittedAt: datetime
    repoFullName: str | None = None
    commitSha: str | None = None
    cutoffCommitSha: str | None = None
    cutoffAt: datetime | None = None
    workflowUrl: str | None = None
    commitUrl: str | None = None
    diffUrl: str | None = None
    diffSummary: dict[str, object] | str | None = None
    testResults: TalentPartnerTestResultsOut | None = None


class CandidateReviewPresentationArtifact(APIModel):
    """Read-only presentation artifact summary for candidate review."""

    kind: Literal["presentation"]
    dayIndex: int
    taskId: int
    taskType: str
    title: str
    submittedAt: datetime
    recording: TalentPartnerRecordingAssetOut | None = None
    transcript: TalentPartnerTranscriptOut | None = None


CandidateReviewDayArtifact = Annotated[
    CandidateReviewMarkdownArtifact
    | CandidateReviewWorkspaceArtifact
    | CandidateReviewPresentationArtifact,
    Field(discriminator="kind"),
]


class CandidateCompletedReviewResponse(APIModel):
    """Read-only completed-session review payload for candidates."""

    candidateSessionId: int
    status: CandidateSessionStatus
    completedAt: datetime
    trial: CandidateTrialSummary
    candidateTimezone: str | None = None
    dayWindows: list[DayWindow] = Field(default_factory=list)
    artifacts: list[CandidateReviewDayArtifact] = Field(default_factory=list)


__all__ = [
    "CandidateCompletedReviewResponse",
    "CandidateReviewDayArtifact",
    "CandidateReviewMarkdownArtifact",
    "CandidateReviewPresentationArtifact",
    "CandidateReviewWorkspaceArtifact",
]
