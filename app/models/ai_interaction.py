import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Column, Field, SQLModel, Text


class AiInteraction(SQLModel, table=True):
    __tablename__ = "AiInteraction"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    ai_session_id: str = Field(foreign_key="AiSession.id", index=True)
    candidate_interview_id: str = Field(foreign_key="CandidateInterview.id", index=True)
    sequence_number: int
    interaction_type: str  # CHAT, INLINE_SUGGEST, INLINE_EDIT
    prompt_text: str = Field(sa_column=Column(Text))
    response_text: str = Field(sa_column=Column(Text))
    tokens_input: int
    tokens_output: int
    latency_ms: int
    accepted: Optional[bool] = Field(default=None)
    edited_after_accept: Optional[bool] = Field(default=None)
    edit_diff: Optional[str] = Field(default=None, sa_column=Column(Text))
    code_context_before: Optional[str] = Field(default=None, sa_column=Column(Text))
    code_context_after: Optional[str] = Field(default=None, sa_column=Column(Text))
    cursor_position_line: Optional[int] = Field(default=None)
    cursor_position_col: Optional[int] = Field(default=None)
    time_since_last_interaction_ms: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
