"""Application module for http routes auth routes workflows."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.recruiters.schemas.recruiters_schemas_recruiters_users_schema import UserRead
from app.shared.auth import rate_limit
from app.shared.auth.shared_auth_current_user_utils import get_authenticated_user
from app.shared.database.shared_database_models_model import User

router = APIRouter()

AUTH_ME_RATE_LIMIT = rate_limit.RateLimitRule(limit=60, window_seconds=60.0)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Read Me",
    description="Return the authenticated recruiter profile for the caller.",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Rate limit exceeded."},
    },
)
async def read_me(
    request: Request,
    current_user: Annotated[User, Depends(get_authenticated_user)],
) -> User:
    """Return the currently authenticated user."""
    if rate_limit.rate_limit_enabled():
        key = rate_limit.rate_limit_key("auth_me", rate_limit.client_id(request))
        rate_limit.limiter.allow(key, AUTH_ME_RATE_LIMIT)
    return current_user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description=(
        "Stateless logout acknowledgment endpoint; client clears local auth" " state."
    ),
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Unexpected logout response failure."
        }
    },
)
async def logout() -> Response:
    """Stateless logout endpoint; backend does not manage sessions or redirects."""
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )
