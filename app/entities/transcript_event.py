"""
Event data structures for transcript processing.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from app.models.enums import TranscriptSender, CodeLanguage


@dataclass
class TranscriptEvent:
    """
    Event data structure for transcript messages.
    
    Contains all necessary information for storing transcript data
    and processing by various subscribers.
    """
    candidate_interview_id: str
    sender: TranscriptSender
    message: str
    timestamp: datetime
    session_id: str
    is_code: bool = False
    code_language: Optional[CodeLanguage] = None
    message_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert event to dictionary for logging/serialization."""
        # Handle timestamp conversion safely
        timestamp_str = self.timestamp
        if hasattr(self.timestamp, 'isoformat'):
            timestamp_str = self.timestamp.isoformat()
        elif isinstance(self.timestamp, str):
            timestamp_str = self.timestamp
        else:
            timestamp_str = str(self.timestamp)
            
        return {
            "candidate_interview_id": self.candidate_interview_id,
            "sender": self.sender.value if isinstance(self.sender, TranscriptSender) else self.sender,
            "message": self.message,
            "timestamp": timestamp_str,
            "session_id": self.session_id,
            "is_code": self.is_code,
            "code_language": self.code_language.value if self.code_language else None,
            "message_id": self.message_id
        }
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"TranscriptEvent(session={self.session_id}, sender={self.sender}, message_len={len(self.message)})"
