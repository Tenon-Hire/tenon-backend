"""Application module for init workflows."""

from fastapi import APIRouter

from . import (
    recruiters_routes_admin_routes_recruiters_admin_routes_demo_ops_routes as demo_ops,
)

router = APIRouter()
router.include_router(demo_ops.router)

__all__ = ["demo_ops", "router"]
