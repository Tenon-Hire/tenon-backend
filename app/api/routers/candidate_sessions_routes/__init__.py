from fastapi import APIRouter

from app.api.routers.candidate_sessions_routes import (
    current_task,
    invites,
    resolve,
    schedule,
)

router = APIRouter()
router.include_router(resolve.router)
router.include_router(schedule.router)
router.include_router(current_task.router)
router.include_router(invites.router)

__all__ = ["router"]
