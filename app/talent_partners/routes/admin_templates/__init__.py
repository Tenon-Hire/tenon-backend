"""Application module for init workflows."""

from fastapi import APIRouter

from . import (
    talent_partners_routes_admin_templates_talent_partners_admin_templates_health_get_routes as health_get,
)
from . import (
    talent_partners_routes_admin_templates_talent_partners_admin_templates_health_run_routes as health_run,
)

router = APIRouter()
router.include_router(health_get.router)
router.include_router(health_run.router)

__all__ = ["health_get", "health_run", "router"]
