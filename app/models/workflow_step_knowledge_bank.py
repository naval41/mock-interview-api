from sqlmodel import SQLModel, Field, Relationship
from typing import Optional


class WorkflowStep_KnowledgeBankBase(SQLModel):
    workflowStepId: str
    knowledgeBankId: str


class WorkflowStep_KnowledgeBank(WorkflowStep_KnowledgeBankBase, table=True):
    __tablename__ = "WorkflowStep_KnowledgeBank"
    
    # Composite primary key
    workflowStepId: str = Field(primary_key=True, foreign_key="WorkflowStep.id")
    knowledgeBankId: str = Field(primary_key=True, foreign_key="KnowledgeBank.id")
    
    # Relationships
    workflowStep: "WorkflowStep" = Relationship(back_populates="knowledgeBanks")
    knowledgeBank: "KnowledgeBank" = Relationship(back_populates="workflowSteps")


class WorkflowStep_KnowledgeBankCreate(WorkflowStep_KnowledgeBankBase):
    pass


class WorkflowStep_KnowledgeBankRead(WorkflowStep_KnowledgeBankBase):
    pass


class WorkflowStep_KnowledgeBankUpdate(SQLModel):
    pass  # No updatable fields
