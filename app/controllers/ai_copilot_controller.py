import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import validate_request
from app.core.database import get_async_session as get_session
from app.dao.ai_interaction_dao import AiInteractionDao
from app.dao.ai_session_dao import AiSessionDao
from app.models.ai_interaction import AiInteraction
from app.models.ai_session import AiSession
from app.schemas.ai_copilot import (
    AiChatRequest,
    AiChatResponse,
    AiInlineRequest,
    AiInlineResponse,
    BudgetStatusResponse,
    InteractionAcceptance,
    StoreSnippetsRequest,
    StoreSnippetsResponse,
)
from app.services.ai_budget_service import AiBudgetService
from app.services.ai_interaction_capture_service import AiInteractionCaptureService
from app.services.ai_proxy_service import AiProxyService

router = APIRouter(prefix="/ai-copilot", tags=["ai-copilot"])

ai_proxy_service = AiProxyService()
budget_service = AiBudgetService()

MAX_HISTORY_INTERACTIONS = 10
DEFAULT_TOKEN_BUDGET = 20000


def context_before(request: AiChatRequest) -> str | None:
    """What the candidate was looking at when they asked.

    A design round has no code, so its Mermaid goes in the same column. The column
    is named `code_context_before`, which is now half a lie, but it is what the
    telemetry means — the artefact the turn was about — and renaming it would take a
    migration across rows that are already written.
    """
    return request.code_context if request.design_context is None else request.design_context


async def get_or_create_session(
    candidate_interview_id: str,
    workflow_step_id: str,
    db: AsyncSession,
) -> AiSession:
    """Find existing session or create a new one for (candidateInterviewId, workflowStepId)."""
    dao = AiSessionDao(db)
    session = await dao.get_by_interview_and_step(candidate_interview_id, workflow_step_id)

    if session:
        if session.status != "ACTIVE":
            raise HTTPException(status_code=400, detail="AI session is not active")
        return session

    new_session = AiSession(
        candidate_interview_id=candidate_interview_id,
        workflow_step_id=workflow_step_id,
        model_provider="gemini",
        model_name="gemini-2.5-flash",
        token_budget_total=DEFAULT_TOKEN_BUDGET,
    )
    return await dao.create(new_session)


def build_history_from_interactions(interactions: List[AiInteraction]) -> List[dict]:
    """Build conversation history from prior CHAT interactions."""
    chat_interactions = [i for i in interactions if i.interaction_type == "CHAT"]
    recent = chat_interactions[-MAX_HISTORY_INTERACTIONS:]

    history = []
    for interaction in recent:
        history.append({"role": "user", "parts": [interaction.prompt_text]})
        history.append({"role": "model", "parts": [interaction.response_text]})
    return history


@router.post("/chat", response_model=AiChatResponse)
async def chat(
    request: AiChatRequest,
    user=Depends(validate_request),
    db: AsyncSession = Depends(get_session),
):
    session_dao = AiSessionDao(db)
    interaction_dao = AiInteractionDao(db)
    capture_service = AiInteractionCaptureService(interaction_dao)

    ai_session = await get_or_create_session(
        request.candidate_interview_id, request.workflow_step_id, db
    )

    session_data = {
        "token_budget_total": ai_session.token_budget_total,
        "tokens_used_input": ai_session.tokens_used_input,
        "tokens_used_output": ai_session.tokens_used_output,
    }
    estimated = budget_service.estimate_input_tokens(request.message)
    check = budget_service.check_budget(session_data, estimated)

    if not check.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Token budget exhausted. No more AI interactions available.",
        )

    prior_interactions = await interaction_dao.get_by_session(ai_session.id, after_sequence=ai_session.reset_at_sequence)
    history = build_history_from_interactions(prior_interactions)

    result = await ai_proxy_service.chat_completion(request, history=history)

    interaction = await capture_service.record_interaction(
        ai_session_id=ai_session.id,
        candidate_interview_id=ai_session.candidate_interview_id,
        interaction_type="CHAT",
        prompt_text=request.message,
        response_text=result["response"],
        tokens_input=result["tokens_input"],
        tokens_output=result["tokens_output"],
        latency_ms=result["latency_ms"],
        code_context_before=context_before(request),
        cursor_position_line=request.cursor_line,
        cursor_position_col=request.cursor_col,
    )

    await session_dao.increment_usage(
        ai_session.id, result["tokens_input"], result["tokens_output"]
    )

    remaining = (
        ai_session.token_budget_total
        - ai_session.tokens_used_input
        - ai_session.tokens_used_output
        - result["tokens_input"]
        - result["tokens_output"]
    )

    return AiChatResponse(
        interaction_id=interaction.id,
        session_id=ai_session.id,
        response=result["response"],
        tokens_used_input=result["tokens_input"],
        tokens_used_output=result["tokens_output"],
        budget_remaining=max(0, remaining),
        budget_total=ai_session.token_budget_total,
    )


@router.post("/chat/stream")
async def chat_stream(
    request: AiChatRequest,
    user=Depends(validate_request),
    db: AsyncSession = Depends(get_session),
):
    session_dao = AiSessionDao(db)
    interaction_dao = AiInteractionDao(db)
    capture_service = AiInteractionCaptureService(interaction_dao)

    ai_session = await get_or_create_session(
        request.candidate_interview_id, request.workflow_step_id, db
    )

    session_data = {
        "token_budget_total": ai_session.token_budget_total,
        "tokens_used_input": ai_session.tokens_used_input,
        "tokens_used_output": ai_session.tokens_used_output,
    }
    estimated = budget_service.estimate_input_tokens(request.message)
    check = budget_service.check_budget(session_data, estimated)

    if not check.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Token budget exhausted. No more AI interactions available.",
        )

    prior_interactions = await interaction_dao.get_by_session(ai_session.id, after_sequence=ai_session.reset_at_sequence)
    history = build_history_from_interactions(prior_interactions)

    async def event_generator():
        full_response = ""
        tokens_input = 0
        tokens_output = 0
        latency_ms = 0

        try:
            async for chunk in ai_proxy_service.chat_completion_stream(request, history=history):
                if chunk["type"] == "token":
                    data = json.dumps({"text": chunk["text"]})
                    yield f"event: token\ndata: {data}\n\n"
                elif chunk["type"] == "done":
                    full_response = chunk["full_response"]
                    tokens_input = chunk["tokens_input"]
                    tokens_output = chunk["tokens_output"]
                    latency_ms = chunk["latency_ms"]

            interaction = await capture_service.record_interaction(
                ai_session_id=ai_session.id,
                candidate_interview_id=ai_session.candidate_interview_id,
                interaction_type="CHAT",
                prompt_text=request.message,
                response_text=full_response,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                code_context_before=context_before(request),
                cursor_position_line=request.cursor_line,
                cursor_position_col=request.cursor_col,
            )

            await session_dao.increment_usage(
                ai_session.id, tokens_input, tokens_output
            )

            remaining = (
                ai_session.token_budget_total
                - ai_session.tokens_used_input
                - ai_session.tokens_used_output
                - tokens_input
                - tokens_output
            )

            done_data = json.dumps({
                "interaction_id": interaction.id,
                "session_id": ai_session.id,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "budget_remaining": max(0, remaining),
                "budget_total": ai_session.token_budget_total,
            })
            yield f"event: done\ndata: {done_data}\n\n"

        except Exception as e:
            error_data = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/inline", response_model=AiInlineResponse)
async def inline_suggest(
    request: AiInlineRequest,
    user=Depends(validate_request),
    db: AsyncSession = Depends(get_session),
):
    session_dao = AiSessionDao(db)
    interaction_dao = AiInteractionDao(db)
    capture_service = AiInteractionCaptureService(interaction_dao)

    ai_session = await get_or_create_session(
        request.candidate_interview_id, request.workflow_step_id, db
    )

    session_data = {
        "token_budget_total": ai_session.token_budget_total,
        "tokens_used_input": ai_session.tokens_used_input,
        "tokens_used_output": ai_session.tokens_used_output,
    }
    estimated = budget_service.estimate_input_tokens(request.prefix + request.suffix)
    check = budget_service.check_budget(session_data, estimated)

    if not check.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Token budget exhausted. No more AI interactions available.",
        )

    result = await ai_proxy_service.inline_completion(request)

    interaction = await capture_service.record_interaction(
        ai_session_id=ai_session.id,
        candidate_interview_id=ai_session.candidate_interview_id,
        interaction_type="INLINE_SUGGEST",
        prompt_text=request.instruction or f"[inline] prefix={len(request.prefix)} suffix={len(request.suffix)}",
        response_text=result["suggestion"],
        tokens_input=result["tokens_input"],
        tokens_output=result["tokens_output"],
        latency_ms=result["latency_ms"],
        code_context_before=request.prefix,
        cursor_position_line=request.cursor_line,
        cursor_position_col=request.cursor_col,
    )

    await session_dao.increment_usage(
        ai_session.id, result["tokens_input"], result["tokens_output"]
    )

    remaining = (
        ai_session.token_budget_total
        - ai_session.tokens_used_input
        - ai_session.tokens_used_output
        - result["tokens_input"]
        - result["tokens_output"]
    )

    return AiInlineResponse(
        interaction_id=interaction.id,
        session_id=ai_session.id,
        suggestion=result["suggestion"],
        tokens_used_input=result["tokens_input"],
        tokens_used_output=result["tokens_output"],
        budget_remaining=max(0, remaining),
        budget_total=ai_session.token_budget_total,
    )


@router.get("/budget/{candidate_interview_id}/{workflow_step_id}", response_model=BudgetStatusResponse)
async def get_budget_status(
    candidate_interview_id: str,
    workflow_step_id: str,
    user=Depends(validate_request),
    db: AsyncSession = Depends(get_session),
):
    ai_session = await get_or_create_session(candidate_interview_id, workflow_step_id, db)
    used_total = ai_session.tokens_used_input + ai_session.tokens_used_output

    return BudgetStatusResponse(
        session_id=ai_session.id,
        candidate_interview_id=ai_session.candidate_interview_id,
        workflow_step_id=ai_session.workflow_step_id,
        total=ai_session.token_budget_total,
        used_input=ai_session.tokens_used_input,
        used_output=ai_session.tokens_used_output,
        used_total=used_total,
        remaining=max(0, ai_session.token_budget_total - used_total),
        interaction_count=ai_session.interaction_count,
        percentage_used=round((used_total / ai_session.token_budget_total) * 100, 1) if ai_session.token_budget_total > 0 else 0,
    )


from pydantic import BaseModel as PydanticBaseModel


class AiResetRequest(PydanticBaseModel):
    candidate_interview_id: str
    workflow_step_id: str


@router.post("/reset")
async def reset_session(
    request: AiResetRequest,
    user=Depends(validate_request),
    db: AsyncSession = Depends(get_session),
):
    """Reset conversation history while preserving token usage.

    Sets the reset_at_sequence marker so future history queries only return
    interactions after this point. Token budget remains consumed.
    """
    interaction_dao = AiInteractionDao(db)
    ai_session = await get_or_create_session(
        request.candidate_interview_id, request.workflow_step_id, db
    )

    current_max = await interaction_dao.get_next_sequence_number(ai_session.id) - 1
    ai_session.reset_at_sequence = current_max
    await db.commit()
    await db.refresh(ai_session)

    used_total = ai_session.tokens_used_input + ai_session.tokens_used_output
    return {
        "status": "reset",
        "session_id": ai_session.id,
        "tokens_preserved": used_total,
        "budget_remaining": max(0, ai_session.token_budget_total - used_total),
    }


@router.post("/accept")
async def record_acceptance(
    request: InteractionAcceptance,
    user=Depends(validate_request),
    db: AsyncSession = Depends(get_session),
):
    interaction_dao = AiInteractionDao(db)
    capture_service = AiInteractionCaptureService(interaction_dao)

    await capture_service.record_acceptance(
        interaction_id=request.interaction_id,
        accepted=request.accepted,
        edited_after_accept=request.edited_after_accept,
        edit_diff=request.edit_diff,
        code_after=request.code_after,
    )

    return {"status": "recorded"}


@router.post("/snippets", response_model=StoreSnippetsResponse)
async def store_snippets(
    request: StoreSnippetsRequest,
    user=Depends(validate_request),
    db: AsyncSession = Depends(get_session),
):
    """Store the code suggestion snippets (and their accept/reject/none status)
    that an AI agent produced for a given interaction within an AI session.

    Snippets are persisted on the owning AiInteraction row, and per-status
    counters are recomputed from the payload.
    """
    interaction_dao = AiInteractionDao(db)
    capture_service = AiInteractionCaptureService(interaction_dao)

    snippets_payload = [s.model_dump(by_alias=True, exclude_none=True) for s in request.snippets]

    try:
        interaction = await capture_service.record_snippets(
            interaction_id=request.interaction_id,
            snippets=snippets_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return StoreSnippetsResponse(
        interaction_id=interaction.id,
        ai_session_id=interaction.ai_session_id,
        total_code_snippets=interaction.total_code_snippets or 0,
        accepted_code_snippets=interaction.accepted_code_snippets or 0,
        rejected_code_snippets=interaction.rejected_code_snippets or 0,
        pending_code_snippets=interaction.pending_code_snippets or 0,
    )
