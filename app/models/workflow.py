from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid
from .enums import WorkflowStepType


class WorkflowBase(SQLModel):
    mockInterviewId: str = Field(unique=True)
    name: str
    description: Optional[str] = None


class Workflow(WorkflowBase, table=True):
    __tablename__ = "Workflow"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign key
    mockInterviewId: str = Field(foreign_key="MockInterview.id")
    
    # Relationships
    mockInterview: "MockInterview" = Relationship(back_populates="workflow")
    steps: Optional[List["WorkflowStep"]] = Relationship(back_populates="workflow")
    planners: Optional[List["CandidateInterviewPlanner"]] = Relationship(back_populates="workflow")


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowRead(WorkflowBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class WorkflowUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None


class WorkflowStepBase(SQLModel):
    workflowId: str = Field(index=True)
    type: WorkflowStepType
    title: str
    description: Optional[str] = None
    duration: int
    customInstructions: Optional[str] = None
    position: int
    prompt: Optional[str] = None


class WorkflowStep(WorkflowStepBase, table=True):
    __tablename__ = "WorkflowStep"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Foreign key
    workflowId: str = Field(foreign_key="Workflow.id")
    
    # Relationships
    workflow: "Workflow" = Relationship(back_populates="steps")
    knowledgeBanks: Optional[List["WorkflowStep_KnowledgeBank"]] = Relationship(back_populates="workflowStep")
    planners: Optional[List["CandidateInterviewPlanner"]] = Relationship(back_populates="workflowStep")
    evaluationCriteria: Optional[List["EvaluationCriteria"]] = Relationship(back_populates="workflowStep")


class WorkflowStepCreate(WorkflowStepBase):
    pass


class WorkflowStepRead(WorkflowStepBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class WorkflowStepUpdate(SQLModel):
    type: Optional[WorkflowStepType] = None
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    customInstructions: Optional[str] = None
    position: Optional[int] = None
    prompt: Optional[str] = None
