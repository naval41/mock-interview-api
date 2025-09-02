from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid
from .enums import TranscriptSender, CodeLanguage


class TranscriptBase(SQLModel):
    candidateInterviewId: str = Field(index=True)
    sender: TranscriptSender
    message: str
    timestamp: datetime
    isCode: bool = Field(default=False)
    codeLanguage: Optional[CodeLanguage] = None


class Transcript(TranscriptBase, table=True):
    __tablename__ = "Transcript"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Foreign key
    candidateInterviewId: str = Field(foreign_key="CandidateInterview.id")
    
    # Relationships
    candidateInterview: "CandidateInterview" = Relationship(back_populates="transcripts")


class TranscriptCreate(TranscriptBase):
    pass


class TranscriptRead(TranscriptBase):
    id: str


class TranscriptUpdate(SQLModel):
    message: Optional[str] = None
    timestamp: Optional[datetime] = None
    isCode: Optional[bool] = None
    codeLanguage: Optional[CodeLanguage] = None
