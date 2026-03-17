from fastapi import APIRouter

from app.api.routers.simulations_routes import (
    candidates,
    candidates_compare,
    create,
    detail,
    invite_create,
    invite_resend,
    lifecycle,
    list_simulations,
    scenario,
    update,
)

router = APIRouter()
router.include_router(list_simulations.router)
router.include_router(create.router)
router.include_router(detail.router, prefix="/simulations")
router.include_router(invite_create.router, prefix="/simulations")
router.include_router(invite_resend.router, prefix="/simulations")
router.include_router(candidates.router, prefix="/simulations")
router.include_router(candidates_compare.router, prefix="/simulations")
router.include_router(lifecycle.router, prefix="/simulations")
router.include_router(scenario.router, prefix="/simulations")
router.include_router(update.router, prefix="/simulations")

__all__ = ["router"]
