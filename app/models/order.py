from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid
from decimal import Decimal
from .enums import OrderStatus


class OrderBase(SQLModel):
    purchaserId: str = Field(index=True)
    interviewId: str = Field(index=True)
    totalAmount: Decimal = Field(decimal_places=2)
    paymentGatewayOrderId: Optional[str] = Field(default=None, unique=True)
    paymentGatewayType: Optional[str] = None
    status: OrderStatus = Field(default=OrderStatus.CREATED)


class Order(OrderBase, table=True):
    __tablename__ = "Orders"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign keys
    serviceId: Optional[str] = Field(default=None, foreign_key="Service.id")
    interviewId: str = Field(foreign_key="MockInterview.id")
    
    # Relationships
    service: Optional["Service"] = Relationship(back_populates="orders")
    mockInterview: "MockInterview" = Relationship(back_populates="orders")
    payments: Optional[List["Payment"]] = Relationship(back_populates="order")
    invoices: Optional[List["Invoice"]] = Relationship(back_populates="order")


class OrderCreate(OrderBase):
    pass


class OrderRead(OrderBase):
    id: str
    createdAt: datetime
    updatedAt: datetime
    serviceId: Optional[str]
    interviewId: str


class OrderUpdate(SQLModel):
    purchaserId: Optional[str] = None
    interviewId: Optional[str] = None
    totalAmount: Optional[Decimal] = None
    paymentGatewayOrderId: Optional[str] = None
    paymentGatewayType: Optional[str] = None
    status: Optional[OrderStatus] = None
    serviceId: Optional[str] = None
