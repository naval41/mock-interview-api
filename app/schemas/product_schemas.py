from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from uuid import UUID


class ProductCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    category: str
    stock_quantity: int = 0


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    stock_quantity: Optional[int] = None


class ProductResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    price: Decimal
    category: str
    is_active: bool
    stock_quantity: int
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[UUID]

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    products: List[ProductResponse]
    total_count: int
    skip: int
    limit: int


class ProductSearchRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    skip: int = 0
    limit: int = 100