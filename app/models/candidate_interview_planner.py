from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid


class CandidateInterviewPlannerBase(SQLModel):
    candidateInterviewId: str = Field(index=True)
    workflowId: str = Field(index=True)
    workflowStepId: str = Field(index=True)
    questionId: str = Field(index=True)
    knowledgeBankId: str = Field(index=True)
    interviewInstructions: Optional[str] = None
    sequence: int = Field(description="Order/sequence of this planner in the interview workflow")
    duration: int = Field(description="Duration in minutes for this planner step")


class CandidateInterviewPlanner(CandidateInterviewPlannerBase, table=True):
    __tablename__ = "CandidateInterviewPlanner"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign keys
    candidateInterviewId: str = Field(foreign_key="CandidateInterview.id")
    workflowId: str = Field(foreign_key="Workflow.id")
    workflowStepId: str = Field(foreign_key="WorkflowStep.id")
    questionId: str = Field(foreign_key="InterviewQuestion.id")
    knowledgeBankId: str = Field(foreign_key="KnowledgeBank.id")
    
    # Relationships
    candidateInterview: "CandidateInterview" = Relationship(back_populates="planners")
    workflow: "Workflow" = Relationship(back_populates="planners")
    workflowStep: "WorkflowStep" = Relationship(back_populates="planners")
    interviewQuestion: "InterviewQuestion" = Relationship(back_populates="candidateInterviewPlanners")
    knowledgeBank: "KnowledgeBank" = Relationship(back_populates="candidateInterviewPlanners")


class CandidateInterviewPlannerCreate(CandidateInterviewPlannerBase):
    pass


class CandidateInterviewPlannerRead(CandidateInterviewPlannerBase):
    id: str
    createdAt: datetime
    updatedAt: datetime
    sequence: int
    duration: int


class CandidateInterviewPlannerUpdate(SQLModel):
    interviewInstructions: Optional[str] = None
    sequence: Optional[int] = Field(None, description="Order/sequence of this planner in the interview workflow")
    duration: Optional[int] = Field(None, description="Duration in minutes for this planner step")
