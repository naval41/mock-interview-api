from typing import Optional

from app.dao.ai_interaction_dao import AiInteractionDao
from app.models.ai_interaction import AiInteraction


class AiInteractionCaptureService:
    def __init__(self, interaction_dao: AiInteractionDao):
        self.dao = interaction_dao

    async def record_interaction(
        self,
        ai_session_id: str,
        candidate_interview_id: str,
        interaction_type: str,
        prompt_text: str,
        response_text: str,
        tokens_input: int,
        tokens_output: int,
        latency_ms: int,
        code_context_before: Optional[str] = None,
        cursor_position_line: Optional[int] = None,
        cursor_position_col: Optional[int] = None,
        time_since_last_interaction_ms: Optional[int] = None,
    ) -> AiInteraction:
        sequence_number = await self.dao.get_next_sequence_number(ai_session_id)

        interaction = AiInteraction(
            ai_session_id=ai_session_id,
            candidate_interview_id=candidate_interview_id,
            sequence_number=sequence_number,
            interaction_type=interaction_type,
            prompt_text=prompt_text,
            response_text=response_text,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            code_context_before=code_context_before,
            cursor_position_line=cursor_position_line,
            cursor_position_col=cursor_position_col,
            time_since_last_interaction_ms=time_since_last_interaction_ms,
        )

        return await self.dao.create(interaction)

    async def record_acceptance(
        self,
        interaction_id: str,
        accepted: bool,
        edited_after_accept: Optional[bool] = None,
        edit_diff: Optional[str] = None,
        code_after: Optional[str] = None,
    ) -> AiInteraction:
        interaction = await self.dao.get_by_id(interaction_id)
        interaction.accepted = accepted
        interaction.edited_after_accept = edited_after_accept
        interaction.edit_diff = edit_diff
        interaction.code_context_after = code_after
        return await self.dao.update(interaction)
