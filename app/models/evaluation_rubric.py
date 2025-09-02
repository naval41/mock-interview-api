from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid
from .enums import QuestionType


class EvaluationRubricBase(SQLModel):
    name: str
    jobLevel: str
    questionType: QuestionType
    totalWeight: int


class EvaluationRubric(EvaluationRubricBase, table=True):
    __tablename__ = "EvaluationRubric"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Relationships
    criteriaLinks: Optional[List["RubricCriteria"]] = Relationship(back_populates="rubric")


class EvaluationRubricCreate(EvaluationRubricBase):
    pass


class EvaluationRubricRead(EvaluationRubricBase):
    id: str


class EvaluationRubricUpdate(SQLModel):
    name: Optional[str] = None
    jobLevel: Optional[str] = None
    questionType: Optional[QuestionType] = None
    totalWeight: Optional[int] = None


class RubricCriteriaBase(SQLModel):
    rubricId: str
    criteriaId: str


class RubricCriteria(RubricCriteriaBase, table=True):
    __tablename__ = "RubricCriteria"
    
    # Composite primary key
    rubricId: str = Field(primary_key=True, foreign_key="EvaluationRubric.id")
    criteriaId: str = Field(primary_key=True, foreign_key="EvaluationCriteria.id")
    
    # Relationships
    rubric: "EvaluationRubric" = Relationship(back_populates="criteriaLinks")
    criteria: "EvaluationCriteria" = Relationship(back_populates="rubrics")


class RubricCriteriaCreate(RubricCriteriaBase):
    pass


class RubricCriteriaRead(RubricCriteriaBase):
    pass


class RubricCriteriaUpdate(SQLModel):
    pass  # No updatable fields
