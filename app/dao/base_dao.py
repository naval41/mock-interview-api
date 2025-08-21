from typing import Generic, TypeVar, Type, Optional, List
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import structlog

logger = structlog.get_logger()

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseDAO(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def create(self, db: AsyncSession, *, obj_in: dict) -> ModelType:
        try:
            db_obj = self.model(**obj_in)
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            logger.info(f"Created {self.model.__name__}", id=str(db_obj.id))
            return db_obj
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating {self.model.__name__}", error=str(e))
            raise

    async def get_by_id(self, db: AsyncSession, id: UUID) -> Optional[ModelType]:
        try:
            result = await db.execute(select(self.model).where(self.model.id == id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id", id=str(id), error=str(e))
            raise

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        try:
            result = await db.execute(select(self.model).offset(skip).limit(limit))
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting multiple {self.model.__name__}", error=str(e))
            raise

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: dict
    ) -> ModelType:
        try:
            for field, value in obj_in.items():
                if hasattr(db_obj, field) and value is not None:
                    setattr(db_obj, field, value)
            
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
            logger.info(f"Updated {self.model.__name__}", id=str(db_obj.id))
            return db_obj
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating {self.model.__name__}", error=str(e))
            raise

    async def delete(self, db: AsyncSession, *, id: UUID) -> Optional[ModelType]:
        try:
            obj = await self.get_by_id(db, id)
            if obj:
                await db.delete(obj)
                await db.commit()
                logger.info(f"Deleted {self.model.__name__}", id=str(id))
            return obj
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting {self.model.__name__}", id=str(id), error=str(e))
            raise