from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid
from .enums import SessionStatus
from sqlalchemy import Column, Enum


class SessionDetailsBase(SQLModel):
    candidateInterviewId: str = Field(unique=True)
    generatedSessionId: str = Field(unique=True)
    status: SessionStatus = Field(
        default=SessionStatus.NOT_STARTED,
        sa_column=Column(
            Enum(SessionStatus, name="SessionStatus"),
            nullable=False,
            server_default=SessionStatus.NOT_STARTED.value,
        ),
    )
    completedAt: Optional[datetime] = None
    roomUrl: Optional[str] = None
    roomToken: Optional[str] = None


class SessionDetails(SessionDetailsBase, table=True):
    __tablename__ = "SessionDetails"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign key
    candidateInterviewId: str = Field(foreign_key="CandidateInterview.id")
    
    # Relationships
    candidateInterview: "CandidateInterview" = Relationship(back_populates="sessionDetails")


class SessionDetailsCreate(SessionDetailsBase):
    pass


class SessionDetailsRead(SessionDetailsBase):
    id: str
    createdAt: datetime


class SessionDetailsUpdate(SQLModel):
    status: Optional[SessionStatus] = None
    completedAt: Optional[datetime] = None
