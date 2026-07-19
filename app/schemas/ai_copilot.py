from typing import Optional, List
from pydantic import BaseModel, Field


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


class SnippetInsertMeta(BaseModel):
    start_line_number: Optional[int] = Field(default=None, alias="startLineNumber")
    end_line_number: Optional[int] = Field(default=None, alias="endLineNumber")
    original_text: Optional[str] = Field(default=None, alias="originalText")
    content_snapshot_after_insert: Optional[str] = Field(
        default=None, alias="contentSnapshotAfterInsert"
    )

    class Config:
        populate_by_name = True


class Snippet(BaseModel):
    id: int
    status: str = "none"  # accepted | rejected | pending | none
    insert_meta: Optional[SnippetInsertMeta] = Field(default=None, alias="insertMeta")

    class Config:
        populate_by_name = True


class StoreSnippetsRequest(BaseModel):
    interaction_id: str = Field(alias="interactionId")
    snippets: List[Snippet] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class StoreSnippetsResponse(BaseModel):
    interaction_id: str
    ai_session_id: str
    total_code_snippets: int
    accepted_code_snippets: int
    rejected_code_snippets: int
    pending_code_snippets: int
    status: str = "stored"
