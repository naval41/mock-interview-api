from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid
from .enums import InterviewLevel


class MockInterviewBase(SQLModel):
    companyName: Optional[str] = None
    companyLogo: Optional[str] = None
    title: str = Field(index=True)
    description: Optional[str] = None
    duration: int
    interviewLevel: InterviewLevel
    prompt: Optional[str] = None


class MockInterview(MockInterviewBase, table=True):
    __tablename__ = "MockInterview"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    candidateInterviews: Optional[List["CandidateInterview"]] = Relationship(back_populates="mockInterview")
    workflow: Optional["Workflow"] = Relationship(back_populates="mockInterview")
    services: Optional[List["Service"]] = Relationship(back_populates="mockInterview")
    orders: Optional[List["Order"]] = Relationship(back_populates="mockInterview")


class MockInterviewCreate(MockInterviewBase):
    pass


class MockInterviewRead(MockInterviewBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class MockInterviewUpdate(SQLModel):
    companyName: Optional[str] = None
    companyLogo: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    interviewLevel: Optional[InterviewLevel] = None
    prompt: Optional[str] = None
