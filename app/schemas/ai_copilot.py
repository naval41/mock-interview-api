from typing import Optional, List
from pydantic import BaseModel


class AiChatRequest(BaseModel):
    candidate_interview_id: str
    workflow_step_id: str
    message: str
    code_context: Optional[str] = None
    cursor_line: Optional[int] = None
    cursor_col: Optional[int] = None
    language: str = "python"


class AiInlineRequest(BaseModel):
    candidate_interview_id: str
    workflow_step_id: str
    prefix: str
    suffix: str
    instruction: Optional[str] = None
    language: str = "python"
    cursor_line: int
    cursor_col: int


class AiChatResponse(BaseModel):
    interaction_id: str
    session_id: str
    response: str
    tokens_used_input: int
    tokens_used_output: int
    budget_remaining: int
    budget_total: int


class AiInlineResponse(BaseModel):
    interaction_id: str
    session_id: str
    suggestion: str
    tokens_used_input: int
    tokens_used_output: int
    budget_remaining: int
    budget_total: int


class BudgetCheckResult(BaseModel):
    allowed: bool
    remaining: int
    total: int
    used: int


class BudgetStatusResponse(BaseModel):
    session_id: str
    candidate_interview_id: str
    workflow_step_id: str
    total: int
    used_input: int
    used_output: int
    used_total: int
    remaining: int
    interaction_count: int
    percentage_used: float


class InteractionAcceptance(BaseModel):
    interaction_id: str
    accepted: bool
    edited_after_accept: Optional[bool] = None
    edit_diff: Optional[str] = None
    code_after: Optional[str] = None
