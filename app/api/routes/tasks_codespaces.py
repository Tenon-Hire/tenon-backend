"""Aggregated tasks router (codespaces, runs, submissions)."""

from contextlib import asynccontextmanager

from fastapi import APIRouter

from app.api.routes.tasks import router as tasks_router
from app.domains.candidate_sessions import service as cs_service
from app.domains.submissions.rate_limits import (
    RATE_LIMIT_RULES as _RATE_LIMIT_RULE,
)
from app.infra.security import rate_limit

router = APIRouter()
router.include_router(tasks_router)


def _rate_limit_or_429(candidate_session_id: int, action: str) -> None:
    if not rate_limit.rate_limit_enabled():
        return
    rule = _RATE_LIMIT_RULE.get(action, rate_limit.RateLimitRule(5, 30.0))
    key = rate_limit.rate_limit_key("tasks", str(candidate_session_id), action)
    rate_limit.limiter.allow(key, rule)


@asynccontextmanager
async def _concurrency_guard(key: str, limit: int):
    if not rate_limit.rate_limit_enabled():
        yield
        return
    async with rate_limit.limiter.concurrency_guard(key, limit):
        yield


async def _compute_current_task(db, cs):
    tasks, _, current, *_ = await cs_service.progress_snapshot(db, cs)
    return current


__all__ = ["router"]
