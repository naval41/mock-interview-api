from typing import Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.base_dao import BaseDAO
from app.models.user import User
import structlog

logger = structlog.get_logger()


class UserDAO(BaseDAO[User]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        try:
            result = await db.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error getting user by email", email=email, error=str(e))
            raise

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        try:
            result = await db.execute(select(User).where(User.username == username))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error getting user by username", username=username, error=str(e))
            raise

    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        from app.core.security import verify_password
        
        user = await self.get_by_email(db, email)
        if not user:
            logger.warning("Authentication failed: user not found", email=email)
            return None
        if not verify_password(password, user.hashed_password):
            logger.warning("Authentication failed: wrong password", email=email)
            return None
        return user

    async def update_last_login(self, db: AsyncSession, user_id) -> Optional[User]:
        from datetime import datetime
        
        try:
            user = await self.get_by_id(db, user_id)
            if user:
                user.last_login = datetime.utcnow()
                db.add(user)
                await db.commit()
                await db.refresh(user)
                logger.info("Updated user last login", user_id=str(user_id))
            return user
        except Exception as e:
            await db.rollback()
            logger.error("Error updating last login", user_id=str(user_id), error=str(e))
            raise


user_dao = UserDAO()