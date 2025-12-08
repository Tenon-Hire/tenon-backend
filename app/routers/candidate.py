from fastapi import APIRouter

router = APIRouter()


@router.get("/session")
async def get_candidate_session():
    return {"message": "candidate session placeholder"}
