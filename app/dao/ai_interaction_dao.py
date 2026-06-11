from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.ai_interaction import AiInteraction


class AiInteractionDao:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, interaction: AiInteraction) -> AiInteraction:
        self.db.add(interaction)
        await self.db.commit()
        await self.db.refresh(interaction)
        return interaction

    async def get_by_id(self, interaction_id: str) -> Optional[AiInteraction]:
        result = await self.db.execute(
            select(AiInteraction).where(AiInteraction.id == interaction_id)
        )
        return result.scalars().first()

    async def get_by_session(self, ai_session_id: str, after_sequence: int = 0) -> List[AiInteraction]:
        result = await self.db.execute(
            select(AiInteraction)
            .where(
                AiInteraction.ai_session_id == ai_session_id,
                AiInteraction.sequence_number > after_sequence,
            )
            .order_by(AiInteraction.sequence_number)
        )
        return result.scalars().all()

    async def get_next_sequence_number(self, ai_session_id: str) -> int:
        interactions = await self.get_by_session(ai_session_id)
        if not interactions:
            return 1
        return interactions[-1].sequence_number + 1

    async def update(self, interaction: AiInteraction) -> AiInteraction:
        await self.db.commit()
        await self.db.refresh(interaction)
        return interaction
