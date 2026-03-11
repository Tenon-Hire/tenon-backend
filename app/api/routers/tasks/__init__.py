from fastapi import APIRouter

from app.api.routers.tasks import draft, handoff_upload, init, poll, run, status, submit

router = APIRouter()
router.include_router(init.router)
router.include_router(status.router)
router.include_router(run.router)
router.include_router(poll.router)
router.include_router(submit.router)
router.include_router(draft.router)
router.include_router(handoff_upload.router)

__all__ = ["router"]
