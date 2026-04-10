"""Application module for auth roles utils workflows."""

from fastapi import HTTPException, status

from app.shared.database.shared_database_models_model import User

TALENT_PARTNER_ONBOARDING_REQUIRED_DETAIL = "Talent Partner onboarding required"
_MISSING = object()


def _ensure_talent_partner_onboarded(user: User) -> None:
    company_id = getattr(user, "company_id", _MISSING)
    if getattr(user, "role", None) == "talent_partner" and company_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=TALENT_PARTNER_ONBOARDING_REQUIRED_DETAIL,
        )


def ensure_talent_partner(user: User) -> None:
    """Enforce Talent Partner role."""
    if getattr(user, "role", None) != "talent_partner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Talent Partner access required",
        )
    _ensure_talent_partner_onboarded(user)


def ensure_talent_partner_or_none(user: User) -> None:
    """Allow Talent Partner or unset role (legacy)."""
    if getattr(user, "role", None) not in {None, "talent_partner"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Talent Partner access required",
        )
    _ensure_talent_partner_onboarded(user)
