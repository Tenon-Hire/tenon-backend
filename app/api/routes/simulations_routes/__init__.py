from fastapi import APIRouter

from app.api.routes.simulations_routes import (
    candidates,
    create,
    detail,
    invite_create,
    invite_resend,
    list_simulations,
)

router = APIRouter()
router.include_router(list_simulations.router)
router.include_router(create.router)
router.include_router(detail.router)
router.include_router(invite_create.router)
router.include_router(invite_resend.router)
router.include_router(candidates.router)

__all__ = ["router"]

