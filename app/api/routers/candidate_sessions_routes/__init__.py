from fastapi import APIRouter

from app.api.routers.candidate_sessions_routes import (
    current_task,
    invites,
    privacy,
    resolve,
    schedule,
)

router = APIRouter()
router.include_router(resolve.router)
router.include_router(schedule.router)
router.include_router(current_task.router)
router.include_router(invites.router)
router.include_router(privacy.router)

__all__ = ["router"]
