from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.core.security import validate_request
from app.models.user import UserRead, User
from sqlmodel import select

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/validate", response_model=UserRead)
async def validate_user(
    user=Depends(validate_request),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = user.get("user_id")
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user_obj = result.scalar_one_or_none()
    if not user_obj:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return UserRead.from_orm(user_obj)

@router.get("/public")
async def public_sample():
    return {"message": "This is a public endpoint. No authentication required."}