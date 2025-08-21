from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.core.security import validate_request

router = APIRouter(prefix="/api", tags=["Interview"])

@router.post("/start-interview")
async def start_interview(
    user=Depends(validate_request),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Start a new interview session.
    Parameters will be added later.
    """
    try:
        # TODO: Add interview start logic and parameters
        return {
            "message": "Interview started successfully",
            "user_id": user.get("user_id"),
            "status": "started"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start interview"
        )
