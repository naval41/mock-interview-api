from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid


class InvoiceBase(SQLModel):
    orderId: str = Field(unique=True)
    invoiceNumber: str = Field(unique=True)
    invoiceUrl: Optional[str] = None
    issuedAt: datetime = Field(default_factory=datetime.utcnow)


class Invoice(InvoiceBase, table=True):
    __tablename__ = "Invoices"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign key
    orderId: str = Field(foreign_key="Orders.id")
    
    # Relationships
    order: "Order" = Relationship(back_populates="invoices")
    invoiceLines: List["InvoiceLine"] = Relationship(back_populates="invoice")


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceRead(InvoiceBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class InvoiceUpdate(SQLModel):
    invoiceNumber: Optional[str] = None
    invoiceUrl: Optional[str] = None
    issuedAt: Optional[datetime] = None


class InvoiceLineBase(SQLModel):
    invoiceId: str
    serviceId: str


class InvoiceLine(InvoiceLineBase, table=True):
    __tablename__ = "InvoiceLines"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign keys
    invoiceId: str = Field(foreign_key="Invoices.id")
    serviceId: str = Field(foreign_key="Service.id")
    
    # Relationships
    invoice: "Invoice" = Relationship(back_populates="invoiceLines")
    service: "Service" = Relationship(back_populates="invoiceLines")


class InvoiceLineCreate(InvoiceLineBase):
    pass


class InvoiceLineRead(InvoiceLineBase):
    id: str
    createdAt: datetime


class InvoiceLineUpdate(SQLModel):
    pass  # No updatable fields
