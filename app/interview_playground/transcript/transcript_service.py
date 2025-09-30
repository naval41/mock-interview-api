"""
Transcript Service for managing transcript processors in interview sessions.
"""

import structlog
from typing import Optional
from .transcript_processor import InterviewTranscriptProcessor

logger = structlog.get_logger()


class TranscriptService:
    """
    Service for managing transcript processing in interview sessions.
    
    This service provides a high-level interface for setting up and managing
    transcript processors for interview conversations.
    """
    
    def __init__(self):
        """Initialize the transcript service."""
        self.transcript_processor = None
        self.is_initialized = False
        
    def setup_processor(self, interview_context=None, enable_database_storage: bool = True) -> InterviewTranscriptProcessor:
        """
        Setup and return a transcript processor for the interview session.
        
        Args:
            interview_context: Optional interview context for session tracking
            enable_database_storage: Whether to enable database storage (default: True)
            
        Returns:
            InterviewTranscriptProcessor instance
        """
        try:
            self.transcript_processor = InterviewTranscriptProcessor(
                interview_context=interview_context,
                enable_database_storage=enable_database_storage
            )
            self.is_initialized = True
            
            session_id = interview_context.session_id if interview_context else "unknown"
            logger.info("Transcript service setup completed", 
                       session_id=session_id,
                       has_context=bool(interview_context),
                       database_storage_enabled=enable_database_storage)
            
            return self.transcript_processor
            
        except Exception as e:
            logger.error("Failed to setup transcript processor", error=str(e))
            raise
    
    def get_processor(self) -> Optional[InterviewTranscriptProcessor]:
        """
        Get the current transcript processor instance.
        
        Returns:
            InterviewTranscriptProcessor instance if initialized, None otherwise
        """
        return self.transcript_processor
    
    def is_ready(self) -> bool:
        """
        Check if the transcript service is ready for use.
        
        Returns:
            True if the service is initialized and ready, False otherwise
        """
        return self.is_initialized and self.transcript_processor is not None
    
    def get_status(self) -> dict:
        """
        Get the current status of the transcript service.
        
        Returns:
            Dictionary containing service status information
        """
        status = {
            "is_initialized": self.is_initialized,
            "has_processor": self.transcript_processor is not None,
            "is_ready": self.is_ready()
        }
        
        if self.transcript_processor:
            status.update(self.transcript_processor.get_session_info())
            
        return status
