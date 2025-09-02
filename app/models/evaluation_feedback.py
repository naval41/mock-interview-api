from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid
from .enums import Recommendation


class EvaluationFeedbackBase(SQLModel):
    candidateInterviewId: str = Field(index=True)
    technical: Optional[str] = None
    behavioral: Optional[str] = None
    strengths: Optional[str] = None
    areasForImprovement: Optional[str] = None
    recommendation: Recommendation


class EvaluationFeedback(EvaluationFeedbackBase, table=True):
    __tablename__ = "EvaluationFeedback"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign key
    candidateInterviewId: str = Field(foreign_key="CandidateInterview.id")
    
    # Relationships
    candidateInterview: "CandidateInterview" = Relationship(back_populates="evaluationFeedbacks")
    evaluationCriteria: Optional[List["EvaluationCriteria"]] = Relationship(back_populates="evaluationFeedback")


class EvaluationFeedbackCreate(EvaluationFeedbackBase):
    pass


class EvaluationFeedbackRead(EvaluationFeedbackBase):
    id: str
    createdAt: datetime


class EvaluationFeedbackUpdate(SQLModel):
    technical: Optional[str] = None
    behavioral: Optional[str] = None
    strengths: Optional[str] = None
    areasForImprovement: Optional[str] = None
    recommendation: Optional[Recommendation] = None
