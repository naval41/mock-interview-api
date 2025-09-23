from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid
from .enums import QuestionType, InterviewDifficulty, CodeLanguage
from sqlalchemy import UniqueConstraint


class InterviewQuestionBase(SQLModel):
    type: QuestionType
    question: str
    timeLimit: int
    prompt: Optional[str] = None
    difficulty: InterviewDifficulty


class InterviewQuestion(InterviewQuestionBase, table=True):
    __tablename__ = "InterviewQuestion"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    codeSignatures: Optional[List["QuestionCodeSignature"]] = Relationship(back_populates="question")
    hints: Optional[List["QuestionHints"]] = Relationship(back_populates="question")
    answers: Optional[List["QuestionAnswers"]] = Relationship(back_populates="question")
    knowledgeMaps: Optional[List["QuestionKnowledgeBankMap"]] = Relationship(back_populates="question")
    candidateInterviewPlanners: Optional[List["CandidateInterviewPlanner"]] = Relationship(back_populates="interviewQuestion")
    evaluationCriteria: Optional[List["EvaluationCriteria"]] = Relationship(back_populates="interviewQuestion")


class InterviewQuestionCreate(InterviewQuestionBase):
    pass


class InterviewQuestionRead(InterviewQuestionBase):
    id: str
    createdAt: datetime
    updatedAt: datetime


class InterviewQuestionUpdate(SQLModel):
    type: Optional[QuestionType] = None
    question: Optional[str] = None
    timeLimit: Optional[int] = None
    prompt: Optional[str] = None
    difficulty: Optional[InterviewDifficulty] = None


class QuestionCodeSignatureBase(SQLModel):
    questionId: str = Field(index=True)
    language: CodeLanguage
    signature: str


class QuestionCodeSignature(QuestionCodeSignatureBase, table=True):
    __tablename__ = "QuestionCodeSignature"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Foreign key
    questionId: str = Field(foreign_key="InterviewQuestion.id")
    
    # Relationships
    question: "InterviewQuestion" = Relationship(back_populates="codeSignatures")


class QuestionCodeSignatureCreate(QuestionCodeSignatureBase):
    pass


class QuestionCodeSignatureRead(QuestionCodeSignatureBase):
    id: str


class QuestionCodeSignatureUpdate(SQLModel):
    language: Optional[CodeLanguage] = None
    signature: Optional[str] = None


class QuestionHintsBase(SQLModel):
    questionId: str = Field(index=True)
    hintSequence: int
    hintInput: Optional[str] = None


class QuestionHints(QuestionHintsBase, table=True):
    __tablename__ = "QuestionHints"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Foreign key
    questionId: str = Field(foreign_key="InterviewQuestion.id")
    
    # Relationships
    question: "InterviewQuestion" = Relationship(back_populates="hints")


class QuestionHintsCreate(QuestionHintsBase):
    pass


class QuestionHintsRead(QuestionHintsBase):
    id: str


class QuestionHintsUpdate(SQLModel):
    hintSequence: Optional[int] = None
    hintInput: Optional[str] = None


class QuestionAnswersBase(SQLModel):
    questionId: str = Field(index=True)
    answerSequence: int
    language: CodeLanguage
    version: Optional[int] = None


class QuestionAnswers(QuestionAnswersBase, table=True):
    __tablename__ = "QuestionAnswers"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Foreign key
    questionId: str = Field(foreign_key="InterviewQuestion.id")
    
    # Relationships
    question: "InterviewQuestion" = Relationship(back_populates="answers")
    candidateInterviewPlanners: Optional[List["CandidateInterviewPlanner"]] = Relationship(back_populates="questionAnswer")


class QuestionAnswersCreate(QuestionAnswersBase):
    pass


class QuestionAnswersRead(QuestionAnswersBase):
    id: str


class QuestionAnswersUpdate(SQLModel):
    answerSequence: Optional[int] = None
    language: Optional[CodeLanguage] = None
    version: Optional[int] = None


class QuestionKnowledgeBankMapBase(SQLModel):
    questionId: str = Field(index=True)
    knowledgeBankId: str = Field(index=True)


class QuestionKnowledgeBankMap(QuestionKnowledgeBankMapBase, table=True):
    __tablename__ = "QuestionKnowledgeBankMap"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Foreign keys
    questionId: str = Field(foreign_key="InterviewQuestion.id")
    knowledgeBankId: str = Field(foreign_key="KnowledgeBank.id")
    
    # Relationships
    question: "InterviewQuestion" = Relationship(back_populates="knowledgeMaps")
    knowledgeBank: "KnowledgeBank" = Relationship(back_populates="questionMaps")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint("questionId", "knowledgeBankId"),
    )


class QuestionKnowledgeBankMapCreate(QuestionKnowledgeBankMapBase):
    pass


class QuestionKnowledgeBankMapRead(QuestionKnowledgeBankMapBase):
    id: str


class QuestionKnowledgeBankMapUpdate(SQLModel):
    pass  # No updatable fields
