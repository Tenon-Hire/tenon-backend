"""Application module for http routes health routes workflows."""

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Health Check",
    description="Lightweight liveness probe for process and routing health.",
    responses={
        500: {"description": "Process is unhealthy."},
    },
)
async def health_check():
    """Liveness probe endpoint."""
    return {"status": "ok"}
