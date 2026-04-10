"""Application module for init workflows."""

from fastapi import APIRouter

from . import (
    trials_routes_trials_routes_trials_routes_candidates_compare_routes as candidates_compare,
)
from . import (
    trials_routes_trials_routes_trials_routes_candidates_routes as candidates,
)
from . import (
    trials_routes_trials_routes_trials_routes_create_routes as create,
)
from . import (
    trials_routes_trials_routes_trials_routes_detail_render_routes as detail_render,
)
from . import (
    trials_routes_trials_routes_trials_routes_detail_routes as detail,
)
from . import (
    trials_routes_trials_routes_trials_routes_invite_create_routes as invite_create,
)
from . import (
    trials_routes_trials_routes_trials_routes_invite_resend_routes as invite_resend,
)
from . import (
    trials_routes_trials_routes_trials_routes_lifecycle_routes as lifecycle,
)
from . import (
    trials_routes_trials_routes_trials_routes_list_trials_routes as list_trials,
)
from . import (
    trials_routes_trials_routes_trials_routes_rate_limits_routes as rate_limits,
)
from . import (
    trials_routes_trials_routes_trials_routes_scenario_routes as scenario,
)
from . import (
    trials_routes_trials_routes_trials_routes_update_routes as update,
)

router = APIRouter()
router.include_router(list_trials.router)
router.include_router(create.router)
router.include_router(detail.router, prefix="/trials")
router.include_router(invite_create.router, prefix="/trials")
router.include_router(invite_resend.router, prefix="/trials")
router.include_router(candidates.router, prefix="/trials")
router.include_router(candidates_compare.router, prefix="/trials")
router.include_router(lifecycle.router, prefix="/trials")
router.include_router(scenario.router, prefix="/trials")
router.include_router(update.router, prefix="/trials")

__all__ = [
    "candidates",
    "candidates_compare",
    "create",
    "detail",
    "detail_render",
    "invite_create",
    "invite_resend",
    "lifecycle",
    "list_trials",
    "rate_limits",
    "router",
    "scenario",
    "update",
]
