from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def session_maker(async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=async_session.bind, expire_on_commit=False, autoflush=False
    )


async def create_trial(async_client, headers: dict[str, str]) -> dict:
    response = await async_client.post(
        "/api/trials",
        headers=headers,
        json={
            "title": "Scenario Generation API",
            "role": "Backend Engineer",
            "techStack": "Python, FastAPI, PostgreSQL",
            "seniority": "Mid",
            "focus": "Validate scenario generation flow",
            "templateKey": "python-fastapi",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
