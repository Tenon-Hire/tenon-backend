from __future__ import annotations

TRANSCRIBE_RECORDING_JOB_TYPE = "transcribe_recording"
TRANSCRIBE_RECORDING_MAX_ATTEMPTS = 5


def transcribe_recording_idempotency_key(recording_id: int) -> str:
    return f"transcribe_recording:{int(recording_id)}"


def build_transcribe_recording_payload(
    *,
    recording_id: int,
    candidate_session_id: int,
    task_id: int,
) -> dict[str, int]:
    return {
        "recordingId": int(recording_id),
        "candidateSessionId": int(candidate_session_id),
        "taskId": int(task_id),
    }


__all__ = [
    "TRANSCRIBE_RECORDING_JOB_TYPE",
    "TRANSCRIBE_RECORDING_MAX_ATTEMPTS",
    "build_transcribe_recording_payload",
    "transcribe_recording_idempotency_key",
]
