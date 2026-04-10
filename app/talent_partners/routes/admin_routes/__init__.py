"""Application module for init workflows."""

from fastapi import APIRouter

from . import (
    talent_partners_routes_admin_routes_talent_partners_admin_routes_demo_ops_routes as demo_ops,
)
from . import (
    talent_partners_routes_admin_routes_talent_partners_admin_routes_dev_session_controls_routes as dev_session_controls,
)

router = APIRouter()
router.include_router(demo_ops.router)

__all__ = ["demo_ops", "dev_session_controls", "router"]
