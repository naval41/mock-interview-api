from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid


class EvaluationCriteriaBase(SQLModel):
    name: str
    category: str
    weight: int
    description: Optional[str] = None
    scoringMethod: str
    minScore: int
    maxScore: int
    workflowStepId: Optional[str] = None
    evaluationFeedbackId: Optional[str] = None
    interviewQuestionId: Optional[str] = None


class EvaluationCriteria(EvaluationCriteriaBase, table=True):
    __tablename__ = "EvaluationCriteria"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Foreign keys
    workflowStepId: Optional[str] = Field(default=None, foreign_key="WorkflowStep.id")
    evaluationFeedbackId: Optional[str] = Field(default=None, foreign_key="EvaluationFeedback.id")
    interviewQuestionId: Optional[str] = Field(default=None, foreign_key="InterviewQuestion.id")
    
    # Relationships
    rubrics: Optional[List["RubricCriteria"]] = Relationship(back_populates="criteria")
    workflowStep: Optional["WorkflowStep"] = Relationship(back_populates="evaluationCriteria")
    evaluationFeedback: Optional["EvaluationFeedback"] = Relationship(back_populates="evaluationCriteria")
    interviewQuestion: Optional["InterviewQuestion"] = Relationship(back_populates="evaluationCriteria")


class EvaluationCriteriaCreate(EvaluationCriteriaBase):
    pass


class EvaluationCriteriaRead(EvaluationCriteriaBase):
    id: str


class EvaluationCriteriaUpdate(SQLModel):
    name: Optional[str] = None
    category: Optional[str] = None
    weight: Optional[int] = None
    description: Optional[str] = None
    scoringMethod: Optional[str] = None
    minScore: Optional[int] = None
    maxScore: Optional[int] = None
