from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dao.base_dao import BaseDAO
from app.models.session_details import SessionDetails
import structlog


logger = structlog.get_logger()


class SessionDetailsDAO(BaseDAO[SessionDetails]):
    def __init__(self) -> None:
        super().__init__(SessionDetails)

    async def get_by_candidate_interview_id(
        self, db: AsyncSession, candidate_interview_id: str
    ) -> Optional[SessionDetails]:
        try:
            stmt = select(SessionDetails).where(
                SessionDetails.candidateInterviewId == candidate_interview_id
            )
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as exc:
            logger.error(
                "Failed to fetch session details by candidate interview id",
                candidate_interview_id=candidate_interview_id,
                error=str(exc),
            )
            raise


session_details_dao = SessionDetailsDAO()







