from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid
from decimal import Decimal
from sqlalchemy import ARRAY, String


class ServiceBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    price: Decimal = Field(decimal_places=2)
    offerPrice: Optional[Decimal] = Field(default=None, decimal_places=2)
    type: str = Field(index=True)
    isActive: bool = Field(default=True)


class ServiceFeatures(SQLModel):
    features: List[str] = Field(default=[])


class Service(ServiceBase, table=True):
    __tablename__ = "Service"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign key for MockInterview
    mockInterviewId: Optional[str] = Field(default=None, foreign_key="MockInterview.id")
    
    # Relationships
    orders: Optional[List["Order"]] = Relationship(back_populates="service")
    invoiceLines: Optional[List["InvoiceLine"]] = Relationship(back_populates="service")
    mockInterview: Optional["MockInterview"] = Relationship(back_populates="services")


class ServiceCreate(ServiceBase, ServiceFeatures):
    pass


class ServiceRead(ServiceBase, ServiceFeatures):
    id: str
    createdAt: datetime
    updatedAt: datetime
    mockInterviewId: Optional[str]


class ServiceUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    offerPrice: Optional[Decimal] = None
    type: Optional[str] = None
    features: Optional[List[str]] = None
    isActive: Optional[bool] = None
    mockInterviewId: Optional[str] = None
