"""Application module for candidates candidate sessions services candidates candidate sessions invite activity service workflows."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.candidate_sessions.repositories import repository as cs_repo


async def last_submission_map(
    db: AsyncSession, session_ids: list[int]
) -> dict[int, datetime | None]:
    """Execute last submission map."""
    return await cs_repo.last_submission_at_bulk(db, session_ids)


__all__ = ["last_submission_map"]
