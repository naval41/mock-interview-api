"""
Data Access Object for Transcript operations.
"""

import structlog
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.transcript import Transcript, TranscriptCreate
from app.dao.base_dao import BaseDAO

logger = structlog.get_logger()


class TranscriptDAO(BaseDAO[Transcript]):
    """Data Access Object for Transcript operations."""
    
    def __init__(self):
        super().__init__(Transcript)
    
    async def create_transcript(
        self, 
        db: AsyncSession, 
        candidate_interview_id: str,
        sender: str,
        message: str,
        timestamp,
        is_code: bool = False,
        code_language: Optional[str] = None
    ) -> Transcript:
        """
        Create a new transcript entry.
        
        Args:
            db: Database session
            candidate_interview_id: ID of the candidate interview
            sender: Message sender (USER/INTERVIEWER)
            message: Transcript message content
            timestamp: Message timestamp
            is_code: Whether message contains code
            code_language: Programming language if is_code is True
            
        Returns:
            Created transcript instance
        """
        try:
            transcript_data = {
                "candidateInterviewId": candidate_interview_id,
                "sender": sender,
                "message": message,
                "timestamp": timestamp,
                "isCode": is_code,
                "codeLanguage": code_language
            }
            
            transcript = await self.create(db, obj_in=transcript_data)
            
            logger.info("Transcript created successfully",
                       transcript_id=transcript.id,
                       candidate_interview_id=candidate_interview_id,
                       sender=sender,
                       message_length=len(message),
                       is_code=is_code)
            
            return transcript
            
        except Exception as e:
            logger.error("Failed to create transcript",
                        candidate_interview_id=candidate_interview_id,
                        sender=sender,
                        error=str(e))
            raise
    
    async def get_transcripts_by_interview(
        self, 
        db: AsyncSession, 
        candidate_interview_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Transcript]:
        """
        Get all transcripts for a specific candidate interview.
        
        Args:
            db: Database session
            candidate_interview_id: ID of the candidate interview
            limit: Maximum number of transcripts to return
            offset: Number of transcripts to skip
            
        Returns:
            List of transcript instances
        """
        try:
            query = select(Transcript).where(
                Transcript.candidateInterviewId == candidate_interview_id
            ).order_by(Transcript.timestamp)
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            result = await db.execute(query)
            transcripts = result.scalars().all()
            
            logger.debug("Retrieved transcripts for interview",
                        candidate_interview_id=candidate_interview_id,
                        count=len(transcripts))
            
            return list(transcripts)
            
        except Exception as e:
            logger.error("Failed to retrieve transcripts",
                        candidate_interview_id=candidate_interview_id,
                        error=str(e))
            raise
    
    async def get_code_transcripts_by_interview(
        self, 
        db: AsyncSession, 
        candidate_interview_id: str
    ) -> List[Transcript]:
        """
        Get all code-related transcripts for a specific candidate interview.
        
        Args:
            db: Database session
            candidate_interview_id: ID of the candidate interview
            
        Returns:
            List of code transcript instances
        """
        try:
            query = select(Transcript).where(
                and_(
                    Transcript.candidateInterviewId == candidate_interview_id,
                    Transcript.isCode == True
                )
            ).order_by(Transcript.timestamp)
            
            result = await db.execute(query)
            transcripts = result.scalars().all()
            
            logger.debug("Retrieved code transcripts for interview",
                        candidate_interview_id=candidate_interview_id,
                        count=len(transcripts))
            
            return list(transcripts)
            
        except Exception as e:
            logger.error("Failed to retrieve code transcripts",
                        candidate_interview_id=candidate_interview_id,
                        error=str(e))
            raise
    
    async def delete_transcripts_by_interview(
        self, 
        db: AsyncSession, 
        candidate_interview_id: str
    ) -> int:
        """
        Delete all transcripts for a specific candidate interview.
        
        Args:
            db: Database session
            candidate_interview_id: ID of the candidate interview
            
        Returns:
            Number of deleted transcripts
        """
        try:
            # First get count for logging
            transcripts = await self.get_transcripts_by_interview(db, candidate_interview_id)
            count = len(transcripts)
            
            # Delete all transcripts
            for transcript in transcripts:
                await self.delete(db, transcript.id)
            
            logger.info("Deleted transcripts for interview",
                       candidate_interview_id=candidate_interview_id,
                       deleted_count=count)
            
            return count
            
        except Exception as e:
            logger.error("Failed to delete transcripts",
                        candidate_interview_id=candidate_interview_id,
                        error=str(e))
            raise
