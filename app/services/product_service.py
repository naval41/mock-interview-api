from typing import List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.product_dao import product_dao
from app.models.product import Product, ProductCreate, ProductUpdate
from datetime import datetime
from uuid import UUID
import structlog

logger = structlog.get_logger()


class ProductService:
    def __init__(self):
        self.product_dao = product_dao

    async def create_product(self, db: AsyncSession, product_create: ProductCreate, created_by: UUID) -> Product:
        try:
            product_data = product_create.dict()
            product_data["created_by"] = created_by
            product_data["created_at"] = datetime.utcnow()

            product = await self.product_dao.create(db, obj_in=product_data)
            logger.info("Product created successfully", product_id=str(product.id), created_by=str(created_by))
            return product

        except Exception as e:
            logger.error("Error creating product", created_by=str(created_by), error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Product creation failed"
            )

    async def get_product(self, db: AsyncSession, product_id: UUID) -> Product:
        try:
            product = await self.product_dao.get_by_id(db, product_id)
            if not product:
                logger.warning("Product not found", product_id=str(product_id))
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product not found"
                )
            return product
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error getting product", product_id=str(product_id), error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve product"
            )

    async def get_products(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Product]:
        try:
            products = await self.product_dao.get_active_products(db, skip=skip, limit=limit)
            logger.info("Retrieved products", count=len(products), skip=skip, limit=limit)
            return products
        except Exception as e:
            logger.error("Error getting products", skip=skip, limit=limit, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve products"
            )

    async def get_products_by_category(self, db: AsyncSession, category: str, skip: int = 0, limit: int = 100) -> List[Product]:
        try:
            products = await self.product_dao.get_by_category(db, category, skip=skip, limit=limit)
            logger.info("Retrieved products by category", category=category, count=len(products))
            return products
        except Exception as e:
            logger.error("Error getting products by category", category=category, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve products by category"
            )

    async def search_products(self, db: AsyncSession, name: str, skip: int = 0, limit: int = 100) -> List[Product]:
        try:
            products = await self.product_dao.search_by_name(db, name, skip=skip, limit=limit)
            logger.info("Searched products by name", name=name, count=len(products))
            return products
        except Exception as e:
            logger.error("Error searching products by name", name=name, error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not search products"
            )

    async def update_product(self, db: AsyncSession, product_id: UUID, product_update: ProductUpdate, user_id: UUID) -> Product:
        try:
            product = await self.get_product(db, product_id)
            
            if product.created_by != user_id:
                logger.warning("Unauthorized product update attempt", product_id=str(product_id), user_id=str(user_id))
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to update this product"
                )

            update_data = product_update.dict(exclude_unset=True)
            if update_data:
                update_data["updated_at"] = datetime.utcnow()
                product = await self.product_dao.update(db, db_obj=product, obj_in=update_data)
                logger.info("Product updated successfully", product_id=str(product_id), user_id=str(user_id))

            return product

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error updating product", product_id=str(product_id), user_id=str(user_id), error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Product update failed"
            )

    async def delete_product(self, db: AsyncSession, product_id: UUID, user_id: UUID) -> bool:
        try:
            product = await self.get_product(db, product_id)
            
            if product.created_by != user_id:
                logger.warning("Unauthorized product delete attempt", product_id=str(product_id), user_id=str(user_id))
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to delete this product"
                )

            deleted_product = await self.product_dao.delete(db, id=product_id)
            if deleted_product:
                logger.info("Product deleted successfully", product_id=str(product_id), user_id=str(user_id))
                return True
            return False

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error deleting product", product_id=str(product_id), user_id=str(user_id), error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Product deletion failed"
            )

    async def get_user_products(self, db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Product]:
        try:
            products = await self.product_dao.get_by_created_by(db, user_id, skip=skip, limit=limit)
            logger.info("Retrieved user products", user_id=str(user_id), count=len(products))
            return products
        except Exception as e:
            logger.error("Error getting user products", user_id=str(user_id), error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve user products"
            )


product_service = ProductService()