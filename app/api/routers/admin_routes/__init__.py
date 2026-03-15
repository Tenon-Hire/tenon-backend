from fastapi import APIRouter

from app.api.routers.admin_routes import demo_ops

router = APIRouter()
router.include_router(demo_ops.router)

__all__ = ["router"]
