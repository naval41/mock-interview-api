from typing import Optional

import structlog

from app.core.database import get_db_session
from app.dao.session_details_dao import session_details_dao
from app.models.session_details import SessionDetails


logger = structlog.get_logger()


class SessionDetailsService:
    async def get_by_candidate_interview_id(
        self, candidate_interview_id: str
    ) -> Optional[SessionDetails]:
        db = await get_db_session()
        try:
            return await session_details_dao.get_by_candidate_interview_id(
                db, candidate_interview_id
            )
        finally:
            await db.close()

    async def create_or_update_session(
        self,
        candidate_interview_id: str,
        generated_session_id: str,
        room_url: str,
        room_token: str,
    ) -> SessionDetails:
        db = await get_db_session()
        try:
            existing = await session_details_dao.get_by_candidate_interview_id(
                db, candidate_interview_id
            )

            if existing:
                existing.generatedSessionId = generated_session_id
                existing.roomUrl = room_url
                existing.roomToken = room_token
                db.add(existing)
                await db.commit()
                await db.refresh(existing)
                logger.info(
                    "Updated session details",
                    candidate_interview_id=candidate_interview_id,
                )
                return existing

            session_details = SessionDetails(
                candidateInterviewId=candidate_interview_id,
                generatedSessionId=generated_session_id,
                roomUrl=room_url,
                roomToken=room_token,
            )
            db.add(session_details)
            await db.commit()
            await db.refresh(session_details)
            logger.info(
                "Created session details", candidate_interview_id=candidate_interview_id
            )
            return session_details
        except Exception as exc:
            await db.rollback()
            logger.error(
                "Failed to create or update session details",
                candidate_interview_id=candidate_interview_id,
                error=str(exc),
            )
            raise
        finally:
            await db.close()


session_details_service = SessionDetailsService()

