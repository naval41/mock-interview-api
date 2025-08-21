from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class User(SQLModel, table=True):
    __tablename__ = "User"

    id: str = Field(primary_key=True, nullable=False)
    email: str = Field(nullable=False, unique=True, index=True)
    password: Optional[str] = Field(default=None)
    provider: str = Field(default="local", nullable=False)
    providerAccountId: Optional[str] = Field(default=None)
    role: str = Field(default="USER", nullable=False)
    avatarUrl: Optional[str] = Field(default=None)
    emailValidated: bool = Field(default=False, nullable=False)
    emailVerificationToken: Optional[str] = Field(default=None, unique=True)
    accessToken: Optional[str] = Field(default=None)
    resetToken: Optional[str] = Field(default=None)
    resetTokenExpiry: Optional[datetime] = Field(default=None)
    createdAt: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updatedAt: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class UserCreate(SQLModel):
    email: str = Field(nullable=False, unique=True, index=True)
    password: str


class UserRead(SQLModel):
    id: str
    email: str
    createdAt: datetime
    updatedAt: datetime


class UserUpdate(SQLModel):
    email: Optional[str] = None
    password: Optional[str] = None
    provider: Optional[str] = None
    providerAccountId: Optional[str] = None
    role: Optional[str] = None
    avatarUrl: Optional[str] = None
    emailValidated: Optional[bool] = None
    emailVerificationToken: Optional[str] = None
    accessToken: Optional[str] = None
    resetToken: Optional[str] = None
    resetTokenExpiry: Optional[datetime] = None