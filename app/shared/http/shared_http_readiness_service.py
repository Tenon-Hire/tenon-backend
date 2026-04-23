"""Application module for Winoe readiness checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import (
    allow_demo_or_test_mode,
    resolve_scenario_generation_config,
    resolve_transcription_config,
    resolve_winoe_report_aggregator_config,
    resolve_winoe_report_code_implementation_config,
    resolve_winoe_report_day1_config,
    resolve_winoe_report_day4_config,
    resolve_winoe_report_day5_config,
)
from app.ai.ai_provider_clients_service import api_key_configured
from app.config import settings
from app.shared.database import async_session_maker, engine
from app.shared.jobs import shared_jobs_worker_heartbeat_service as heartbeat_service
from app.shared.jobs.repositories import repository as jobs_repo

ReadinessStatus = Literal["ready", "not_ready", "skipped"]

_AI_FEATURE_RESOLVERS = {
    "scenarioGeneration": resolve_scenario_generation_config,
    "transcription": resolve_transcription_config,
    "winoeReportDay1": resolve_winoe_report_day1_config,
    "winoeReportCodeImplementationReviewer": resolve_winoe_report_code_implementation_config,
    "winoeReportDay4": resolve_winoe_report_day4_config,
    "winoeReportDay5": resolve_winoe_report_day5_config,
    "winoeReportAggregator": resolve_winoe_report_aggregator_config,
}

_REQUIRED_TABLES = {
    "candidate_sessions",
    "jobs",
    "scenario_versions",
    "tasks",
    "trials",
    "worker_heartbeats",
}

_REQUIRED_FOREIGN_KEYS = {
    "candidate_sessions": {
        ("trial_id", "trials", ("id",)),
        ("scenario_version_id", "scenario_versions", ("id",)),
    },
    "scenario_versions": {
        ("trial_id", "trials", ("id",)),
    },
    "tasks": {
        ("trial_id", "trials", ("id",)),
    },
}


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    """Machine-readable readiness check result."""

    status: ReadinessStatus
    code: str
    detail: str
    data: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "code": self.code,
            "detail": self.detail,
        }
        if self.data:
            payload["data"] = self.data
        return payload


def _utc_now(now: datetime | None = None) -> datetime:
    resolved = now or datetime.now(UTC)
    if resolved.tzinfo is None:
        return resolved.replace(tzinfo=UTC)
    return resolved.astimezone(UTC)


def _readiness_check(
    *,
    status: ReadinessStatus,
    code: str,
    detail: str,
    data: dict[str, Any] | None = None,
) -> ReadinessCheck:
    return ReadinessCheck(status=status, code=code, detail=detail, data=data)


def _aggregate_status(checks: list[ReadinessCheck]) -> ReadinessStatus:
    if any(check.status == "not_ready" for check in checks):
        return "not_ready"
    if all(check.status == "skipped" for check in checks):
        return "skipped"
    return "ready"


def _normalize_fks(
    raw_foreign_keys: list[dict[str, Any]],
) -> set[tuple[str, str, tuple[str, ...]]]:
    normalized: set[tuple[str, str, tuple[str, ...]]] = set()
    for fk in raw_foreign_keys:
        constrained = tuple(
            str(column) for column in fk.get("constrained_columns") or ()
        )
        referred_table = str(fk.get("referred_table") or "")
        referred_columns = tuple(
            str(column) for column in fk.get("referred_columns") or ()
        )
        normalized.add(
            (constrained[0] if constrained else "", referred_table, referred_columns)
        )
    return normalized


def _inspect_schema(sync_connection) -> ReadinessCheck:
    inspector = inspect(sync_connection)
    existing_tables = set(inspector.get_table_names())
    missing_tables = sorted(_REQUIRED_TABLES - existing_tables)
    missing_foreign_keys: dict[str, list[str]] = {}

    for table_name, expected_fks in _REQUIRED_FOREIGN_KEYS.items():
        if table_name not in existing_tables:
            continue
        actual_fks = _normalize_fks(inspector.get_foreign_keys(table_name))
        missing_specs = [
            f"{column}->{referred_table}.{','.join(referred_columns)}"
            for column, referred_table, referred_columns in sorted(expected_fks)
            if (column, referred_table, referred_columns) not in actual_fks
        ]
        if missing_specs:
            missing_foreign_keys[table_name] = missing_specs

    if missing_tables or missing_foreign_keys:
        data: dict[str, Any] = {}
        if missing_tables:
            data["missingTables"] = missing_tables
        if missing_foreign_keys:
            data["missingForeignKeys"] = missing_foreign_keys
        return _readiness_check(
            status="not_ready",
            code="schema_mismatch",
            detail="Required database tables or foreign keys are missing.",
            data=data,
        )

    return _readiness_check(
        status="ready",
        code="schema_ok",
        detail="Required database tables and foreign keys are present.",
    )


def _format_heartbeat_age(
    heartbeat: object,
    *,
    now: datetime,
) -> int | None:
    last_seen = getattr(heartbeat, "last_heartbeat_at", None)
    if isinstance(last_seen, datetime):
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        return max(0, int((now - last_seen).total_seconds()))
    return None


async def check_database_readiness() -> ReadinessCheck:
    """Validate the database connection and schema shape."""
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(_inspect_schema)
    except Exception:
        return _readiness_check(
            status="not_ready",
            code="database_unavailable",
            detail="Database connection or schema inspection failed.",
        )


async def check_worker_readiness(
    *,
    session_maker: async_sessionmaker[AsyncSession] = async_session_maker,
    now: datetime | None = None,
) -> ReadinessCheck:
    """Validate that the worker heartbeat is fresh."""
    resolved_now = _utc_now(now)
    async with session_maker() as db:
        heartbeat = await jobs_repo.get_latest_worker_heartbeat(
            db, service_name=heartbeat_service.DEFAULT_WORKER_SERVICE_NAME
        )
    if heartbeat is None:
        return _readiness_check(
            status="not_ready",
            code="heartbeat_missing",
            detail="No worker heartbeat has been recorded.",
        )
    if (
        getattr(heartbeat, "status", None)
        == heartbeat_service.WORKER_HEARTBEAT_STATUS_STOPPED
    ):
        return _readiness_check(
            status="not_ready",
            code="heartbeat_stopped",
            detail="The latest worker heartbeat is marked stopped.",
            data={
                "serviceName": heartbeat.service_name,
                "instanceId": heartbeat.instance_id,
            },
        )
    if not heartbeat_service.is_worker_heartbeat_fresh(
        heartbeat,
        now=resolved_now,
    ):
        return _readiness_check(
            status="not_ready",
            code="heartbeat_stale",
            detail="The latest worker heartbeat is stale.",
            data={
                "serviceName": heartbeat.service_name,
                "instanceId": heartbeat.instance_id,
                "ageSeconds": _format_heartbeat_age(heartbeat, now=resolved_now),
                "staleAfterSeconds": settings.WORKER_HEARTBEAT_STALE_SECONDS,
            },
        )
    return _readiness_check(
        status="ready",
        code="heartbeat_fresh",
        detail="Worker heartbeat is fresh.",
        data={
            "serviceName": heartbeat.service_name,
            "instanceId": heartbeat.instance_id,
            "ageSeconds": _format_heartbeat_age(heartbeat, now=resolved_now),
        },
    )


def _check_ai_feature(name: str, config) -> ReadinessCheck:
    runtime_mode = str(getattr(config, "runtime_mode", "") or "").strip().lower()
    provider = str(getattr(config, "provider", "") or "").strip().lower()
    if allow_demo_or_test_mode(runtime_mode):
        return _readiness_check(
            status="skipped",
            code="demo_mode",
            detail=f"{name} is running in demo/test mode.",
            data={"runtimeMode": runtime_mode, "provider": provider},
        )
    if provider == "openai":
        if api_key_configured(settings.OPENAI_API_KEY):
            return _readiness_check(
                status="ready",
                code="provider_ready",
                detail=f"{name} is ready with the OpenAI provider.",
                data={"runtimeMode": runtime_mode, "provider": provider},
            )
        return _readiness_check(
            status="not_ready",
            code="no_provider_configured",
            detail=f"{name} is missing an OpenAI API key.",
            data={"runtimeMode": runtime_mode, "provider": provider},
        )
    if provider == "anthropic":
        if api_key_configured(settings.ANTHROPIC_API_KEY):
            return _readiness_check(
                status="ready",
                code="provider_ready",
                detail=f"{name} is ready with the Anthropic provider.",
                data={"runtimeMode": runtime_mode, "provider": provider},
            )
        return _readiness_check(
            status="not_ready",
            code="no_provider_configured",
            detail=f"{name} is missing an Anthropic API key.",
            data={"runtimeMode": runtime_mode, "provider": provider},
        )
    return _readiness_check(
        status="not_ready",
        code="unsupported_provider",
        detail=f"{name} uses an unsupported AI provider.",
        data={"runtimeMode": runtime_mode, "provider": provider},
    )


async def check_ai_readiness() -> ReadinessCheck:
    """Validate the configured AI provider surface."""
    checks = {
        feature_name: _check_ai_feature(feature_name, resolver())
        for feature_name, resolver in _AI_FEATURE_RESOLVERS.items()
    }
    status = _aggregate_status(list(checks.values()))
    return _readiness_check(
        status=status,
        code="ai_providers_ready"
        if status != "not_ready"
        else "ai_providers_unhealthy",
        detail="AI provider readiness validated.",
        data={"checks": {name: check.as_dict() for name, check in checks.items()}},
    )


def _check_github_readiness() -> ReadinessCheck:
    github_cfg = settings.github
    token = str(github_cfg.GITHUB_TOKEN or "").strip()
    org = str(github_cfg.GITHUB_ORG or "").strip()
    template_owner = str(github_cfg.GITHUB_TEMPLATE_OWNER or "").strip()
    if settings.DEMO_MODE and not token and not org and not template_owner:
        return _readiness_check(
            status="skipped",
            code="demo_mode",
            detail="GitHub readiness is skipped in demo mode.",
        )
    if not token:
        return _readiness_check(
            status="not_ready",
            code="no_provider_configured",
            detail="GitHub token is missing.",
        )
    if not org and not template_owner:
        return _readiness_check(
            status="not_ready",
            code="missing_github_org",
            detail="GitHub org or template owner is missing.",
        )
    return _readiness_check(
        status="ready",
        code="provider_ready",
        detail="GitHub configuration is ready.",
        data={
            "apiBase": github_cfg.GITHUB_API_BASE,
            "orgConfigured": bool(org),
            "templateOwnerConfigured": bool(template_owner),
        },
    )


def _check_email_readiness() -> ReadinessCheck:
    email_cfg = settings.email
    provider = str(email_cfg.WINOE_EMAIL_PROVIDER or "console").strip().lower()
    sender = str(email_cfg.WINOE_EMAIL_FROM or "").strip()
    if provider == "console":
        return _readiness_check(
            status="ready",
            code="provider_ready",
            detail="Console email provider is ready for local/demo use.",
            data={"provider": provider, "senderConfigured": bool(sender)},
        )
    if provider == "resend":
        if str(email_cfg.WINOE_RESEND_API_KEY or "").strip():
            return _readiness_check(
                status="ready",
                code="provider_ready",
                detail="Resend email provider is configured.",
                data={"provider": provider, "senderConfigured": bool(sender)},
            )
        return _readiness_check(
            status="not_ready",
            code="no_provider_configured",
            detail="Resend API key is missing.",
            data={"provider": provider},
        )
    if provider == "sendgrid":
        if str(email_cfg.SENDGRID_API_KEY or "").strip():
            return _readiness_check(
                status="ready",
                code="provider_ready",
                detail="SendGrid email provider is configured.",
                data={"provider": provider, "senderConfigured": bool(sender)},
            )
        return _readiness_check(
            status="not_ready",
            code="no_provider_configured",
            detail="SendGrid API key is missing.",
            data={"provider": provider},
        )
    if provider == "smtp":
        if str(email_cfg.SMTP_HOST or "").strip():
            return _readiness_check(
                status="ready",
                code="provider_ready",
                detail="SMTP email provider is configured.",
                data={"provider": provider, "senderConfigured": bool(sender)},
            )
        return _readiness_check(
            status="not_ready",
            code="no_provider_configured",
            detail="SMTP host is missing.",
            data={"provider": provider},
        )
    return _readiness_check(
        status="not_ready",
        code="unsupported_provider",
        detail="Email provider is unsupported.",
        data={"provider": provider},
    )


def _check_media_readiness() -> ReadinessCheck:
    media_cfg = settings.storage_media
    provider = str(media_cfg.MEDIA_STORAGE_PROVIDER or "fake").strip().lower()
    if provider == "fake":
        return _readiness_check(
            status="ready",
            code="provider_ready",
            detail="Fake media storage provider is ready for local/demo use.",
            data={"provider": provider},
        )
    if provider == "s3":
        missing = [
            name
            for name, value in (
                ("MEDIA_S3_ENDPOINT", media_cfg.MEDIA_S3_ENDPOINT),
                ("MEDIA_S3_BUCKET", media_cfg.MEDIA_S3_BUCKET),
                ("MEDIA_S3_ACCESS_KEY_ID", media_cfg.MEDIA_S3_ACCESS_KEY_ID),
                ("MEDIA_S3_SECRET_ACCESS_KEY", media_cfg.MEDIA_S3_SECRET_ACCESS_KEY),
            )
            if not str(value or "").strip()
        ]
        if missing:
            return _readiness_check(
                status="not_ready",
                code="no_provider_configured",
                detail="S3 media storage is missing required settings.",
                data={"provider": provider, "missingFields": missing},
            )
        return _readiness_check(
            status="ready",
            code="provider_ready",
            detail="S3 media storage provider is configured.",
            data={"provider": provider},
        )
    return _readiness_check(
        status="not_ready",
        code="unsupported_provider",
        detail="Media storage provider is unsupported.",
        data={"provider": provider},
    )


async def build_readiness_payload(
    *,
    session_maker: async_sessionmaker[AsyncSession] = async_session_maker,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return the readiness payload consumed by the HTTP endpoint."""
    resolved_now = _utc_now(now)
    checks: dict[str, Any] = {}

    database_check = await check_database_readiness()
    checks["database"] = database_check.as_dict()

    worker_check = await check_worker_readiness(
        session_maker=session_maker, now=resolved_now
    )
    checks["worker"] = worker_check.as_dict()

    ai_check = await check_ai_readiness()
    checks["ai"] = ai_check.as_dict()

    github_check = _check_github_readiness()
    checks["github"] = github_check.as_dict()

    email_check = _check_email_readiness()
    checks["email"] = email_check.as_dict()

    media_check = _check_media_readiness()
    checks["media"] = media_check.as_dict()

    statuses: list[ReadinessCheck] = [
        database_check,
        worker_check,
        ai_check,
        github_check,
        email_check,
        media_check,
    ]
    overall_status = (
        "ready"
        if all(check.status != "not_ready" for check in statuses)
        else "not_ready"
    )
    return {
        "status": overall_status,
        "checkedAt": resolved_now.isoformat().replace("+00:00", "Z"),
        "checks": checks,
    }


check_github_readiness = _check_github_readiness
check_email_readiness = _check_email_readiness
check_media_readiness = _check_media_readiness


__all__ = [
    "ReadinessCheck",
    "build_readiness_payload",
    "check_ai_readiness",
    "check_database_readiness",
    "check_email_readiness",
    "check_github_readiness",
    "check_media_readiness",
    "check_worker_readiness",
]
