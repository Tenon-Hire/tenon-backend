from fastapi import HTTPException, status

from app.models.user import User


def ensure_recruiter(user: User, *, allow_none: bool = False) -> None:
    """Enforce recruiter role, optionally allowing unset roles."""
    role = getattr(user, "role", None)
    allowed = {"recruiter"}
    if allow_none:
        allowed.add(None)

    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Recruiter access required"
        )
