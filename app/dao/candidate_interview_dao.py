from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.base_dao import BaseDAO
from app.models.candidate_interview import CandidateInterview, CandidateInterviewStatus
import structlog

logger = structlog.get_logger()


class CandidateInterviewDAO(BaseDAO[CandidateInterview]):
    def __init__(self):
        super().__init__(CandidateInterview)

    async def get_by_user_id(self, db: AsyncSession, user_id: str) -> List[CandidateInterview]:
        """Get all interviews for a specific user"""
        try:
            result = await db.execute(
                select(CandidateInterview).where(CandidateInterview.userId == user_id)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting interviews by user_id", user_id=user_id, error=str(e))
            raise

    async def get_by_mock_interview_id(self, db: AsyncSession, mock_interview_id: str) -> List[CandidateInterview]:
        """Get all interviews for a specific mock interview template"""
        try:
            result = await db.execute(
                select(CandidateInterview).where(CandidateInterview.mockInterviewId == mock_interview_id)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting interviews by mock_interview_id", mock_interview_id=mock_interview_id, error=str(e))
            raise

    async def get_by_mock_interview_and_user(
        self, 
        db: AsyncSession, 
        mock_interview_id: str, 
        user_id: str
    ) -> Optional[CandidateInterview]:
        """Get a specific interview by mock interview ID and user ID"""
        try:
            result = await db.execute(
                select(CandidateInterview).where(
                    CandidateInterview.mockInterviewId == mock_interview_id,
                    CandidateInterview.userId == user_id
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error getting interview by mock_interview_id and user_id", 
                        mock_interview_id=mock_interview_id, user_id=user_id, error=str(e))
            raise

    async def get_by_status(self, db: AsyncSession, status: CandidateInterviewStatus) -> List[CandidateInterview]:
        """Get all interviews with a specific status"""
        try:
            result = await db.execute(
                select(CandidateInterview).where(CandidateInterview.status == status)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting interviews by status", status=status, error=str(e))
            raise

    async def get_user_interviews_by_status(
        self, 
        db: AsyncSession, 
        user_id: str, 
        status: CandidateInterviewStatus
    ) -> List[CandidateInterview]:
        """Get interviews for a specific user with a specific status"""
        try:
            result = await db.execute(
                select(CandidateInterview).where(
                    CandidateInterview.userId == user_id,
                    CandidateInterview.status == status
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting user interviews by status", user_id=user_id, status=status, error=str(e))
            raise

    async def update_status(
        self, 
        db: AsyncSession, 
        interview_id: str, 
        status: CandidateInterviewStatus
    ) -> Optional[CandidateInterview]:
        """Update the status of a candidate interview"""
        try:
            interview = await self.get_by_id(db, interview_id)
            if interview:
                interview.status = status
                db.add(interview)
                await db.commit()
                await db.refresh(interview)
                logger.info("Updated interview status", interview_id=interview_id, status=status)
            return interview
        except Exception as e:
            await db.rollback()
            logger.error("Error updating interview status", interview_id=interview_id, status=status, error=str(e))
            raise

    async def update_recording_url(
        self, 
        db: AsyncSession, 
        interview_id: str, 
        recording_url: str
    ) -> Optional[CandidateInterview]:
        """Update the recording URL of a candidate interview"""
        try:
            interview = await self.get_by_id(db, interview_id)
            if interview:
                interview.recordingUrl = recording_url
                db.add(interview)
                await db.commit()
                await db.refresh(interview)
                logger.info("Updated interview recording URL", interview_id=interview_id)
            return interview
        except Exception as e:
            await db.rollback()
            logger.error("Error updating interview recording URL", interview_id=interview_id, error=str(e))
            raise

    async def update_code_editor_snapshot(
        self, 
        db: AsyncSession, 
        interview_id: str, 
        snapshot: str
    ) -> Optional[CandidateInterview]:
        """Update the code editor snapshot of a candidate interview"""
        try:
            interview = await self.get_by_id(db, interview_id)
            if interview:
                interview.codeEditorSnapshot = snapshot
                db.add(interview)
                await db.commit()
                await db.refresh(interview)
                logger.info("Updated interview code editor snapshot", interview_id=interview_id)
            return interview
        except Exception as e:
            await db.rollback()
            logger.error("Error updating interview code editor snapshot", interview_id=interview_id, error=str(e))
            raise

    async def update_design_editor_snapshot(
        self, 
        db: AsyncSession, 
        interview_id: str, 
        snapshot: str
    ) -> Optional[CandidateInterview]:
        """Update the design editor snapshot of a candidate interview"""
        try:
            interview = await self.get_by_id(db, interview_id)
            if interview:
                interview.designEditorSnapshot = snapshot
                db.add(interview)
                await db.commit()
                await db.refresh(interview)
                logger.info("Updated interview design editor snapshot", interview_id=interview_id)
            return interview
        except Exception as e:
            await db.rollback()
            logger.error("Error updating interview design editor snapshot", interview_id=interview_id, error=str(e))
            raise

    async def get_active_interviews(self, db: AsyncSession) -> List[CandidateInterview]:
        """Get all interviews that are currently in progress"""
        try:
            result = await db.execute(
                select(CandidateInterview).where(
                    CandidateInterview.status == CandidateInterviewStatus.IN_PROGRESS
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting active interviews", error=str(e))
            raise

    async def get_completed_interviews(self, db: AsyncSession) -> List[CandidateInterview]:
        """Get all completed interviews"""
        try:
            result = await db.execute(
                select(CandidateInterview).where(
                    CandidateInterview.status == CandidateInterviewStatus.COMPLETED
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting completed interviews", error=str(e))
            raise


# Create a singleton instance
candidate_interview_dao = CandidateInterviewDAO()
