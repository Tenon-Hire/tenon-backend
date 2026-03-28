"""Application module for init workflows."""

from fastapi import APIRouter

from . import (
    submissions_routes_submissions_routes_submissions_routes_detail_routes as detail,
)
from . import (
    submissions_routes_submissions_routes_submissions_routes_list_routes as list,
)

router = APIRouter(tags=["submissions"])
router.include_router(detail.router)
router.include_router(list.router)

__all__ = ["detail", "list", "router"]
