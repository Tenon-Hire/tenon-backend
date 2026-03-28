from __future__ import annotations

from contextlib import contextmanager

import pytest

from app.main import app


@pytest.fixture
def auth_header_factory():
    def _build(user) -> dict[str, str]:
        return {"x-dev-user-email": user.email}

    return _build


@pytest.fixture
def candidate_header_factory():
    def _build(
        candidate_session_id, token: str | None = None, *, email: str | None = None
    ) -> dict[str, str]:
        session_id = (
            candidate_session_id.id
            if hasattr(candidate_session_id, "id")
            else candidate_session_id
        )
        if not token:
            if email is None and hasattr(candidate_session_id, "invite_email"):
                email = candidate_session_id.invite_email
            if not email:
                raise ValueError("Candidate email required for candidate headers")
            token = f"candidate:{email}"
        return {
            "x-candidate-session-id": str(session_id),
            "Authorization": f"Bearer {token}",
        }

    return _build


@pytest.fixture
def override_dependencies():
    @contextmanager
    def _override(overrides: dict):
        app.dependency_overrides.update(overrides)
        try:
            yield
        finally:
            for dep in overrides:
                app.dependency_overrides.pop(dep, None)

    return _override
