from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
async def login():
    # Will implement in M0 once User model + JWT are ready
    return {"message": "login placeholder"}
