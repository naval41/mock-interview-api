"""
Event subscribers for transcript processing.
"""

from .database_subscriber import TranscriptDatabaseSubscriber

__all__ = [
    "TranscriptDatabaseSubscriber"
]
