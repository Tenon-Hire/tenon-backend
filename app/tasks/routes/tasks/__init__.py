"""Application module for init workflows."""

from fastapi import APIRouter

from . import (
    tasks_routes_tasks_tasks_codespace_init_routes,
    tasks_routes_tasks_tasks_codespace_status_routes,
    tasks_routes_tasks_tasks_draft_routes,
    tasks_routes_tasks_tasks_handoff_upload_routes,
    tasks_routes_tasks_tasks_run_poll_routes,
    tasks_routes_tasks_tasks_run_routes,
    tasks_routes_tasks_tasks_submit_routes,
)

# Temporary aliases while imports migrate.
init = tasks_routes_tasks_tasks_codespace_init_routes
status = tasks_routes_tasks_tasks_codespace_status_routes
run = tasks_routes_tasks_tasks_run_routes
poll = tasks_routes_tasks_tasks_run_poll_routes
submit = tasks_routes_tasks_tasks_submit_routes
draft = tasks_routes_tasks_tasks_draft_routes
handoff_upload = tasks_routes_tasks_tasks_handoff_upload_routes

router = APIRouter()
router.include_router(tasks_routes_tasks_tasks_codespace_init_routes.router)
router.include_router(tasks_routes_tasks_tasks_codespace_status_routes.router)
router.include_router(tasks_routes_tasks_tasks_run_routes.router)
router.include_router(tasks_routes_tasks_tasks_run_poll_routes.router)
router.include_router(tasks_routes_tasks_tasks_submit_routes.router)
router.include_router(tasks_routes_tasks_tasks_draft_routes.router)
router.include_router(tasks_routes_tasks_tasks_handoff_upload_routes.router)

__all__ = ["router"]
