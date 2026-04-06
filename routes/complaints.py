from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.complaints_db import get_all_complaints

router = APIRouter()


class ComplaintOut(BaseModel):
    id: int
    complaint: str
    issue: str
    location: str
    priority: str
    timestamp: str


@router.get("/complaints", response_model=List[ComplaintOut])
async def list_complaints() -> List[ComplaintOut]:
    try:
        rows = get_all_complaints()
        return [
            ComplaintOut(
                id=r.id,
                complaint=r.complaint,
                issue=r.issue,
                location=r.location,
                priority=r.priority,
                timestamp=r.timestamp,
            )
            for r in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to retrieve complaints.") from exc

