from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid
from decimal import Decimal
from .enums import PaymentStatus, PaymentMethod


class PaymentBase(SQLModel):
    orderId: str
    razorpayPaymentId: Optional[str] = Field(default=None, unique=True)
    amount: Decimal = Field(decimal_places=2)
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    paymentMethod: Optional[PaymentMethod] = None
    cardLast4: Optional[str] = None
    cardholderName: Optional[str] = None
    paidAt: Optional[datetime] = None


class Payment(PaymentBase, table=True):
    __tablename__ = "Payments"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign key
    orderId: str = Field(foreign_key="Orders.id")
    
    # Relationships
    order: "Order" = Relationship(back_populates="payments")


class PaymentCreate(PaymentBase):
    pass


class PaymentRead(PaymentBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class PaymentUpdate(SQLModel):
    razorpayPaymentId: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[PaymentStatus] = None
    paymentMethod: Optional[PaymentMethod] = None
    cardLast4: Optional[str] = None
    cardholderName: Optional[str] = None
    paidAt: Optional[datetime] = None
