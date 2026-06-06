from datetime import datetime
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.ai_session import AiSession


class AiSessionDao:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session: AiSession) -> AiSession:
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: str) -> Optional[AiSession]:
        result = await self.db.execute(
            select(AiSession).where(AiSession.id == session_id)
        )
        return result.scalars().first()

    async def get_by_candidate_interview(
        self, candidate_interview_id: str
    ) -> Optional[AiSession]:
        result = await self.db.execute(
            select(AiSession).where(
                AiSession.candidate_interview_id == candidate_interview_id
            )
        )
        return result.scalars().first()

    async def get_by_interview_and_step(
        self, candidate_interview_id: str, workflow_step_id: str
    ) -> Optional[AiSession]:
        result = await self.db.execute(
            select(AiSession).where(
                AiSession.candidate_interview_id == candidate_interview_id,
                AiSession.workflow_step_id == workflow_step_id,
            )
        )
        return result.scalars().first()

    async def increment_usage(
        self, session_id: str, input_tokens: int, output_tokens: int
    ) -> AiSession:
        session = await self.get_by_id(session_id)
        session.tokens_used_input += input_tokens
        session.tokens_used_output += output_tokens
        session.interaction_count += 1
        session.last_interaction_at = datetime.utcnow()
        if session.first_interaction_at is None:
            session.first_interaction_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(session)
        return session
