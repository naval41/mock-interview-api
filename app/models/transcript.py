from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SQLEnum
from typing import Optional
from datetime import datetime
import uuid
from .enums import TranscriptSender, CodeLanguage


class TranscriptBase(SQLModel):
    candidateInterviewId: str = Field(index=True)
    sender: TranscriptSender = Field(
        sa_column=Column(
            "sender", 
            SQLEnum(
                *[sender.value for sender in TranscriptSender],
                name="TranscriptSender",
                create_constraint=False,  # Don't create constraint, assume it exists
                validate_strings=True
            ),
            nullable=False
        )
    )
    message: str
    timestamp: datetime
    isCode: bool = Field(default=False)
    codeLanguage: Optional[CodeLanguage] = Field(
        default=None,
        sa_column=Column(
            "codeLanguage", 
            SQLEnum(
                *[lang.value for lang in CodeLanguage],
                name="CodeLanguage",
                create_constraint=False,  # Don't create constraint, assume it exists
                validate_strings=True
            ),
            nullable=True
        )
    )


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
