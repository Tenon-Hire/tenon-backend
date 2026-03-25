from __future__ import annotations

from app.recruiters.schemas.recruiters_schemas_recruiters_admin_ops_schema import (
    CandidateSessionResetResponse,
    JobRequeueResponse,
    MediaRetentionPurgeResponse,
    SimulationFallbackResponse,
)


def build_reset_response(result) -> CandidateSessionResetResponse:
    return CandidateSessionResetResponse(
        candidateSessionId=result.candidate_session_id,
        status=result.status,
        resetTo=result.reset_to,
        auditId=result.audit_id,
    )


def build_requeue_response(result) -> JobRequeueResponse:
    return JobRequeueResponse(
        jobId=result.job_id,
        previousStatus=result.previous_status,
        newStatus=result.new_status,
        auditId=result.audit_id,
    )


def build_fallback_response(result) -> SimulationFallbackResponse:
    return SimulationFallbackResponse(
        simulationId=result.simulation_id,
        activeScenarioVersionId=result.active_scenario_version_id,
        applyTo=result.apply_to,
        auditId=result.audit_id,
    )


def build_media_purge_response(result) -> MediaRetentionPurgeResponse:
    return MediaRetentionPurgeResponse(
        status="ok",
        scannedCount=result.scanned_count,
        purgedCount=result.purged_count,
        failedCount=result.failed_count,
        purgedRecordingIds=result.purged_recording_ids,
    )
