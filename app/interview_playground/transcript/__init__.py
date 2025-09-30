"""
Transcript package for interview playground.
Handles transcript processing, storage, and management for interview sessions.
Includes pub-sub event system for decoupled database storage.
"""

# Package version
__version__ = "1.0.0"

# Import main classes when the package is imported
from .transcript_processor import InterviewTranscriptProcessor
from .transcript_service import TranscriptService
from .events import TranscriptEventBus
from app.entities.transcript_event import TranscriptEvent
from .events.subscribers import TranscriptDatabaseSubscriber
from app.dao.transcript_dao import TranscriptDAO

__all__ = [
    "InterviewTranscriptProcessor",
    "TranscriptService",
    "TranscriptEventBus",
    "TranscriptEvent",
    "TranscriptDatabaseSubscriber",
    "TranscriptDAO"
]
