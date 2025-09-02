from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid
from .enums import CandidateInterviewStatus


class CandidateInterviewBase(SQLModel):
    userId: str = Field(index=True)
    mockInterviewId: str = Field(index=True)
    status: CandidateInterviewStatus = Field(default=CandidateInterviewStatus.PENDING)
    recordingUrl: Optional[str] = None
    codeEditorSnapshot: Optional[str] = None
    designEditorSnapshot: Optional[str] = None


class CandidateInterview(CandidateInterviewBase, table=True):
    __tablename__ = "CandidateInterview"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign keys
    userId: str = Field(foreign_key="User.id")
    mockInterviewId: str = Field(foreign_key="MockInterview.id")
    
    # Relationships
    user: "User" = Relationship(back_populates="candidateInterviews")
    mockInterview: "MockInterview" = Relationship(back_populates="candidateInterviews")
    sessionDetails: Optional["SessionDetails"] = Relationship(back_populates="candidateInterview")
    evaluationFeedbacks: Optional[List["EvaluationFeedback"]] = Relationship(back_populates="candidateInterview")
    transcripts: Optional[List["Transcript"]] = Relationship(back_populates="candidateInterview")
    planners: Optional[List["CandidateInterviewPlanner"]] = Relationship(back_populates="candidateInterview")


class CandidateInterviewCreate(CandidateInterviewBase):
    pass


class CandidateInterviewRead(CandidateInterviewBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class CandidateInterviewUpdate(SQLModel):
    status: Optional[CandidateInterviewStatus] = None
    recordingUrl: Optional[str] = None
    codeEditorSnapshot: Optional[str] = None
    designEditorSnapshot: Optional[str] = None
