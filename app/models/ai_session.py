import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AiSession(SQLModel, table=True):
    __tablename__ = "AiSession"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    candidate_interview_id: str = Field(foreign_key="CandidateInterview.id", index=True)
    workflow_step_id: str = Field(foreign_key="WorkflowStep.id")
    model_provider: str = Field(default="gemini")
    model_name: str = Field(default="gemini-2.0-flash")
    token_budget_total: int = Field(default=10000)
    tokens_used_input: int = Field(default=0)
    tokens_used_output: int = Field(default=0)
    interaction_count: int = Field(default=0)
    reset_at_sequence: int = Field(default=0)
    first_interaction_at: Optional[datetime] = Field(default=None)
    last_interaction_at: Optional[datetime] = Field(default=None)
    status: str = Field(default="ACTIVE")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
