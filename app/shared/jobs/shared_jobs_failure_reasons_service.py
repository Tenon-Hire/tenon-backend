"""Safe failure reason normalization for durable jobs."""

from __future__ import annotations

import re

from app.shared.jobs.repositories.shared_jobs_repositories_repository_shared_repository import (
    sanitize_error,
)

SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(github[_-]?token[\"'=:\s]+)[^\s,;}]+"),
    re.compile(r"(?i)(auth0[_-]?[a-z0-9_]*secret[\"'=:\s]+)[^\s,;}]+"),
    re.compile(r"(?i)(api[_-]?key[\"'=:\s]+)[^\s,;}]+"),
    re.compile(r"(?i)(token[\"'=:\s]+)[^\s,;}]+"),
)

STACK_TRACE_MARKERS = (
    "traceback (most recent call last)",
    'file "',
    "sqlalchemy.exc.",
)


def redact_failure_text(value: str | None) -> str:
    """Return a compact error string with common secret shapes removed."""
    text = sanitize_error(value or "")
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(r"\1[redacted]", text)
    return text


def failure_category(error: str | None) -> str:
    """Classify a stored job error into a safe operational category."""
    lowered = (error or "").lower()
    if not lowered:
        return "unclassified"
    if "github" in lowered:
        return "github"
    if "transcrib" in lowered or "unsupported file" in lowered:
        return "media_transcription"
    if "evaluation" in lowered or "winoe report" in lowered or "model_" in lowered:
        return "evaluation"
    if "timeout" in lowered or "timed out" in lowered:
        return "provider_timeout"
    if "rate limit" in lowered or "429" in lowered:
        return "provider_rate_limit"
    return "unclassified"


def human_failure_reason(*, job_type: str | None, error: str | None) -> str:
    """Return a concise, safe, human-readable failure reason."""
    redacted = redact_failure_text(error)
    lowered = redacted.lower()
    category = failure_category(redacted)
    if any(marker in lowered for marker in STACK_TRACE_MARKERS):
        redacted = ""

    if category == "github":
        return "GitHub operation failed after the job reached its retry limit."
    if category == "media_transcription":
        if redacted:
            return f"Media transcription failed: {redacted}"
        return "Media transcription failed."
    if category == "evaluation":
        if "timeout" in lowered or "timed out" in lowered:
            return "Evaluation provider timed out while generating the Winoe Report."
        return "Evaluation failed while generating the Winoe Report."
    if category == "provider_timeout":
        return "Provider timed out while processing the job."
    if category == "provider_rate_limit":
        return "Provider rate limit prevented the job from completing."
    if job_type:
        return (
            f"{job_type.replace('_', ' ').title()} failed with an unclassified error. "
            "Use the job id to inspect server logs."
        )
    return (
        "Job failed with an unclassified error. Use the job id to inspect server logs."
    )


__all__ = ["failure_category", "human_failure_reason", "redact_failure_text"]
