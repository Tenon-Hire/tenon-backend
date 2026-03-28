"""Application module for auth dependencies db utils workflows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database.shared_database_models_model import User


async def lookup_user(db: AsyncSession, email: str) -> User | None:
    """Look up user."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
