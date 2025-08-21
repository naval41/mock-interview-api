from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid
from decimal import Decimal


class ProductBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    price: Decimal = Field(decimal_places=2)
    category: str
    is_active: bool = Field(default=True)
    stock_quantity: int = Field(default=0)


class Product(ProductBase, table=True):
    __tablename__ = "products"
    
    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by: Optional[uuid.UUID] = Field(foreign_key="users.id")


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[uuid.UUID]


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    stock_quantity: Optional[int] = None