from typing import List, Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.base_dao import BaseDAO
from app.models.product import Product
from uuid import UUID
import structlog

logger = structlog.get_logger()


class ProductDAO(BaseDAO[Product]):
    def __init__(self):
        super().__init__(Product)

    async def get_by_category(self, db: AsyncSession, category: str, skip: int = 0, limit: int = 100) -> List[Product]:
        try:
            result = await db.execute(
                select(Product)
                .where(Product.category == category)
                .where(Product.is_active == True)
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting products by category", category=category, error=str(e))
            raise

    async def get_active_products(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Product]:
        try:
            result = await db.execute(
                select(Product)
                .where(Product.is_active == True)
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting active products", error=str(e))
            raise

    async def search_by_name(self, db: AsyncSession, name: str, skip: int = 0, limit: int = 100) -> List[Product]:
        try:
            result = await db.execute(
                select(Product)
                .where(Product.name.ilike(f"%{name}%"))
                .where(Product.is_active == True)
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error searching products by name", name=name, error=str(e))
            raise

    async def get_by_created_by(self, db: AsyncSession, created_by: UUID, skip: int = 0, limit: int = 100) -> List[Product]:
        try:
            result = await db.execute(
                select(Product)
                .where(Product.created_by == created_by)
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting products by creator", created_by=str(created_by), error=str(e))
            raise


product_dao = ProductDAO()