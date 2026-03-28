"""Application module for init workflows."""

from fastapi import APIRouter

from . import (
    simulations_routes_simulations_routes_simulations_routes_candidates_compare_routes as candidates_compare,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_candidates_routes as candidates,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_create_routes as create,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_detail_render_routes as detail_render,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_detail_routes as detail,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_invite_create_routes as invite_create,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_invite_resend_routes as invite_resend,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_lifecycle_routes as lifecycle,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_list_simulations_routes as list_simulations,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_rate_limits_routes as rate_limits,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_scenario_routes as scenario,
)
from . import (
    simulations_routes_simulations_routes_simulations_routes_update_routes as update,
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

__all__ = [
    "candidates",
    "candidates_compare",
    "create",
    "detail",
    "detail_render",
    "invite_create",
    "invite_resend",
    "lifecycle",
    "list_simulations",
    "rate_limits",
    "router",
    "scenario",
    "update",
]
