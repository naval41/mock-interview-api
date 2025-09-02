from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid
from .enums import InterviewDifficulty


class KnowledgeBankBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    difficulty: InterviewDifficulty
    category: str = Field(index=True)


class KnowledgeBank(KnowledgeBankBase, table=True):
    __tablename__ = "KnowledgeBank"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    workflowSteps: Optional[List["WorkflowStep_KnowledgeBank"]] = Relationship(back_populates="knowledgeBank")
    questionMaps: Optional[List["QuestionKnowledgeBankMap"]] = Relationship(back_populates="knowledgeBank")
    candidateInterviewPlanners: Optional[List["CandidateInterviewPlanner"]] = Relationship(back_populates="knowledgeBank")


class KnowledgeBankCreate(KnowledgeBankBase):
    pass


class KnowledgeBankRead(KnowledgeBankBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class KnowledgeBankUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[InterviewDifficulty] = None
    category: Optional[str] = None
