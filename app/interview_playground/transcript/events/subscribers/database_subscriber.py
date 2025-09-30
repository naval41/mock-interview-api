"""
Database subscriber for transcript events.
Handles storing transcript events in the database.
"""

import structlog
from typing import Optional
from sqlalchemy import select
from app.core.database import get_db_session
from app.dao.transcript_dao import TranscriptDAO
from app.entities.transcript_event import TranscriptEvent
from app.models.candidate_interview import CandidateInterview

logger = structlog.get_logger()


class TranscriptDatabaseSubscriber:
    """
    Database subscriber for transcript events.
    
    Handles storing transcript events in the database asynchronously
    without blocking the main transcript processing pipeline.
    """
    
    def __init__(self):
        """Initialize database subscriber."""
        self.dao = TranscriptDAO()
        self.processed_count = 0
        self.error_count = 0
        self.validated_interviews = set()  # Cache of validated interview IDs
        
    async def handle_transcript_event(self, event: TranscriptEvent) -> None:
        """
        Handle transcript event by storing it in the database.
        
        Args:
            event: Transcript event to process and store
        """
        # Check if candidate interview exists before attempting to store
        if not await self._validate_candidate_interview(event.candidate_interview_id):
            logger.warning("Skipping transcript storage - candidate interview not found",
                          candidate_interview_id=event.candidate_interview_id,
                          session_id=event.session_id,
                          sender=event.sender,
                          message_preview=event.message[:50] + "..." if len(event.message) > 50 else event.message)
            return
        
        db = None
        try:
            # Get database session
            db = await get_db_session()
            
            # Store transcript in database
            transcript = await self.dao.create_transcript(
                db=db,
                candidate_interview_id=event.candidate_interview_id,
                sender=event.sender,  # This should be the enum object, not string
                message=event.message,
                timestamp=event.timestamp,
                is_code=event.is_code,
                code_language=event.code_language
            )
            
            self.processed_count += 1
            
            logger.info("Transcript stored in database",
                       transcript_id=transcript.id,
                       candidate_interview_id=event.candidate_interview_id,
                       session_id=event.session_id,
                       sender=event.sender,
                       message_length=len(event.message),
                       is_code=event.is_code,
                       processed_count=self.processed_count)
            
        except Exception as e:
            self.error_count += 1
            
            # Check if it's a foreign key violation for candidate interview
            if "ForeignKeyViolationError" in str(e) and "candidateInterviewId" in str(e):
                logger.warning("Skipping transcript storage - candidate interview not found in database",
                              candidate_interview_id=event.candidate_interview_id,
                              session_id=event.session_id,
                              sender=event.sender,
                              message_preview=event.message[:50] + "..." if len(event.message) > 50 else event.message)
            else:
                logger.error("Failed to store transcript in database",
                            candidate_interview_id=event.candidate_interview_id,
                            session_id=event.session_id,
                            sender=event.sender,
                            error=str(e),
                            error_count=self.error_count,
                            event_data=event.to_dict())
            
            # Don't re-raise - we don't want database errors to break transcript display
            
        finally:
            if db:
                await db.close()
    
    async def _validate_candidate_interview(self, candidate_interview_id: str) -> bool:
        """
        Validate that a candidate interview exists in the database.
        
        Args:
            candidate_interview_id: ID to validate
            
        Returns:
            True if the interview exists, False otherwise
        """
        # Check cache first
        if candidate_interview_id in self.validated_interviews:
            return True
        
        # Skip validation for "unknown" or test IDs
        if candidate_interview_id in ["unknown", "test"]:
            return False
        
        db = None
        try:
            db = await get_db_session()
            
            # Check if candidate interview exists
            query = select(CandidateInterview).where(CandidateInterview.id == candidate_interview_id)
            result = await db.execute(query)
            candidate_interview = result.scalar_one_or_none()
            
            if candidate_interview:
                # Cache the validated ID
                self.validated_interviews.add(candidate_interview_id)
                logger.debug("Candidate interview validated",
                           candidate_interview_id=candidate_interview_id)
                return True
            else:
                logger.debug("Candidate interview not found",
                           candidate_interview_id=candidate_interview_id)
                return False
                
        except Exception as e:
            logger.error("Error validating candidate interview",
                        candidate_interview_id=candidate_interview_id,
                        error=str(e))
            return False
        finally:
            if db:
                await db.close()
    
    async def handle_transcript_session_started(self, event: TranscriptEvent) -> None:
        """
        Handle transcript session started event.
        
        Args:
            event: Session started event
        """
        logger.info("Transcript session started",
                   candidate_interview_id=event.candidate_interview_id,
                   session_id=event.session_id)
    
    async def handle_transcript_session_ended(self, event: TranscriptEvent) -> None:
        """
        Handle transcript session ended event.
        
        Args:
            event: Session ended event
        """
        logger.info("Transcript session ended",
                   candidate_interview_id=event.candidate_interview_id,
                   session_id=event.session_id,
                   processed_count=self.processed_count,
                   error_count=self.error_count)
    
    def get_status(self) -> dict:
        """
        Get subscriber status for monitoring.
        
        Returns:
            Dictionary with subscriber statistics
        """
        return {
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "validated_interviews_count": len(self.validated_interviews),
            "validated_interviews": list(self.validated_interviews),
            "success_rate": (
                self.processed_count / (self.processed_count + self.error_count)
                if (self.processed_count + self.error_count) > 0 else 0
            )
        }
