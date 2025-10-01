from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Enum as SQLEnum, String
from typing import Optional
from datetime import datetime
import uuid
from .enums import CodeLanguage


class QuestionSolutionBase(SQLModel):
    answer: str = Field(description="The code solution/answer")
    questionId: str = Field(index=True, foreign_key="InterviewQuestion.id")
    candidateInterviewId: str = Field(foreign_key="CandidateInterview.id")


class QuestionSolution(QuestionSolutionBase, table=True):
    __tablename__ = "QuestionSolution"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Explicitly define the enum column to match the existing database enum type
    language: CodeLanguage = Field(
        sa_column=Column(
            "language", 
            SQLEnum(
                *[lang.value for lang in CodeLanguage],
                name="CodeLanguage",
                create_constraint=False,  # Don't create constraint, assume it exists
                validate_strings=True
            ),
            nullable=False
        )
    )
    
    # Timestamp fields
    createdAt: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updatedAt: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    
    # Relationships
    question: "InterviewQuestion" = Relationship()
    candidateInterview: "CandidateInterview" = Relationship()


class QuestionSolutionCreate(QuestionSolutionBase):
    language: CodeLanguage = Field(description="Programming language of the solution")


class QuestionSolutionRead(QuestionSolutionBase):
    id: str
    language: CodeLanguage


class QuestionSolutionUpdate(SQLModel):
    answer: Optional[str] = None
    language: Optional[CodeLanguage] = None
