import structlog
from typing import Optional

from app.core.database import get_session_context
from app.dao.ai_session_dao import AiSessionDao
from app.models.ai_session import AiSession

logger = structlog.get_logger()


class AiPhaseProcessor:
    async def initialize_session(
        self,
        candidate_interview_id: str,
        workflow_step_id: str,
        token_budget: int = 10000,
        model_provider: str = "gemini",
        model_name: str = "gemini-2.0-flash",
    ) -> AiSession:
        async with get_session_context() as db:
            dao = AiSessionDao(db)

            existing = await dao.get_by_candidate_interview(candidate_interview_id)
            if existing and existing.workflow_step_id == workflow_step_id:
                logger.info(
                    "ai_session_already_exists",
                    session_id=existing.id,
                    candidate_interview_id=candidate_interview_id,
                )
                return existing

            session = AiSession(
                candidate_interview_id=candidate_interview_id,
                workflow_step_id=workflow_step_id,
                model_provider=model_provider,
                model_name=model_name,
                token_budget_total=token_budget,
            )

            created = await dao.create(session)
            logger.info(
                "ai_session_created",
                session_id=created.id,
                candidate_interview_id=candidate_interview_id,
                token_budget=token_budget,
            )
            return created

    async def finalize_session(self, candidate_interview_id: str) -> Optional[AiSession]:
        async with get_session_context() as db:
            dao = AiSessionDao(db)
            session = await dao.get_by_candidate_interview(candidate_interview_id)
            if session:
                session.status = "COMPLETED"
                await db.commit()
                logger.info(
                    "ai_session_finalized",
                    session_id=session.id,
                    tokens_used=session.tokens_used_input + session.tokens_used_output,
                    interactions=session.interaction_count,
                )
            return session
