from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Smart Electricity Complaint Analyzer is running"}

