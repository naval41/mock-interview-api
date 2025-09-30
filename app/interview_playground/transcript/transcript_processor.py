"""
Transcript Processor implementation for interview sessions.
Based on Pipecat's TranscriptProcessor for handling conversation transcripts.
Includes internal pub-sub mechanism for decoupled database storage.
"""

import structlog
from datetime import datetime
from typing import Optional
from pipecat.processors.transcript_processor import TranscriptProcessor as PipecatTranscriptProcessor
from app.models.enums import TranscriptSender
from .events import TranscriptEventBus
from app.entities.transcript_event import TranscriptEvent
from .events.subscribers import TranscriptDatabaseSubscriber

logger = structlog.get_logger()


class InterviewTranscriptProcessor:
    """
    Interview-specific transcript processor wrapper around Pipecat's TranscriptProcessor.
    
    This class provides a factory for creating and managing conversation transcript processors
    with shared event handling for both user and assistant messages.
    """
    
    def __init__(self, interview_context=None, enable_database_storage: bool = True):
        """
        Initialize the interview transcript processor.
        
        Args:
            interview_context: Optional interview context for session tracking
            enable_database_storage: Whether to enable database storage (default: True)
        """
        self.interview_context = interview_context
        self.transcript_processor = PipecatTranscriptProcessor()
        
        # Extract context information
        self.session_id = interview_context.session_id if interview_context else "unknown"
        self.candidate_interview_id = (
            getattr(interview_context, 'candidate_interview_id', None) or
            getattr(interview_context, 'mock_interview_id', None) or
            "unknown"
        )
        
        # Internal event system
        self.event_bus = TranscriptEventBus()
        self.db_subscriber = TranscriptDatabaseSubscriber() if enable_database_storage else None
        
        # Setup internal pub-sub system
        self._setup_internal_event_system()
        
        # Setup pipecat event handlers
        self._setup_pipecat_event_handlers()
        
        logger.info("Interview transcript processor initialized", 
                   session_id=self.session_id,
                   candidate_interview_id=self.candidate_interview_id,
                   database_storage_enabled=enable_database_storage)
    
    def _setup_internal_event_system(self):
        """Setup internal pub-sub system within processor."""
        if self.db_subscriber:
            # Subscribe database handler to transcript events
            self.event_bus.subscribe("transcript_created", self.db_subscriber.handle_transcript_event)
            self.event_bus.subscribe("session_started", self.db_subscriber.handle_transcript_session_started)
            self.event_bus.subscribe("session_ended", self.db_subscriber.handle_transcript_session_ended)
            
            logger.info("Database subscriber registered for transcript events",
                       session_id=self.session_id)
    
    def _setup_pipecat_event_handlers(self):
        """Setup event handlers for transcript updates."""
        
        @self.transcript_processor.event_handler("on_transcript_update")
        async def handle_transcript_update(processor, frame):
            """Handle transcript updates from both user and assistant."""
            try:
                processor_type = "USER" if hasattr(processor, '_role') and processor._role == "user" else "ASSISTANT"
                
                # Print transcript to console (existing behavior)
                self._print_transcript_update(processor, frame, processor_type)
                
                # Publish events for database storage
                await self._publish_transcript_events(frame, processor_type)
                           
            except Exception as e:
                logger.error("Error handling transcript update", 
                           session_id=self.session_id,
                           error=str(e))
                print(f"❌ Error handling transcript update: {e}")
    
    def _print_transcript_update(self, processor, frame, processor_type):
        """Print transcript update to console."""
        print("\n" + "=" * 80)
        print(f"📝 TRANSCRIPT UPDATE - {processor_type}")
        print("=" * 80)
        print(f"Session ID: {self.session_id}")
        print(f"Processor: {type(processor).__name__}")
        print(f"Messages Count: {len(frame.messages)}")
        print("=" * 80)
        
        for i, message in enumerate(frame.messages, 1):
            role_icon = "🗣️" if message.role == "user" else "🤖"
            print(f"[{i}] {role_icon} {message.role.upper()}:")
            print(f"    Content: {message.content}")
            print(f"    Timestamp: {message.timestamp}")
            if message.user_id:
                print(f"    User ID: {message.user_id}")
            print("-" * 40)
        
        print("=" * 80 + "\n")
        
        # Log structured data
        logger.info("Transcript updated",
                   session_id=self.session_id,
                   processor_type=processor_type,
                   message_count=len(frame.messages),
                   messages=[{
                       "role": msg.role,
                       "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                       "timestamp": msg.timestamp
                   } for msg in frame.messages])
    
    async def _publish_transcript_events(self, frame, processor_type):
        """Publish transcript events to internal event bus."""
        for message in frame.messages:
            # Map Pipecat role to our TranscriptSender enum
            sender = self._map_role_to_sender(message.role)
            
            # Create transcript event
            event = TranscriptEvent(
                candidate_interview_id=self.candidate_interview_id,
                sender=sender,
                message=message.content,
                timestamp=self._convert_timestamp(message.timestamp),
                session_id=self.session_id,
                is_code=self._detect_code_content(message.content),
                code_language=None,  # TODO: Implement code language detection
                message_id=getattr(message, 'id', None)
            )
            
            # Publish to internal event bus
            await self.event_bus.publish("transcript_created", event)
    
    def _convert_timestamp(self, timestamp) -> datetime:
        """
        Convert timestamp to datetime object, handling various input types.
        
        Args:
            timestamp: Can be datetime object, string, or None
            
        Returns:
            datetime object
        """
        if timestamp is None:
            return datetime.utcnow()
        
        if isinstance(timestamp, datetime):
            return timestamp
        
        if isinstance(timestamp, str):
            try:
                # Try to parse ISO format string
                # Handle timezone-aware strings by removing timezone info for fromisoformat
                if timestamp.endswith('+00:00'):
                    timestamp = timestamp.replace('+00:00', '')
                elif timestamp.endswith('Z'):
                    timestamp = timestamp.replace('Z', '')
                
                # Try fromisoformat first (Python 3.7+)
                return datetime.fromisoformat(timestamp)
            except (ValueError, TypeError) as e:
                logger.warning("Failed to parse timestamp string, using current time",
                             timestamp=timestamp,
                             error=str(e))
                return datetime.utcnow()
        
        # For any other type, try to convert to string first, then parse
        try:
            timestamp_str = str(timestamp)
            if timestamp_str.endswith('+00:00'):
                timestamp_str = timestamp_str.replace('+00:00', '')
            elif timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str.replace('Z', '')
            return datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError) as e:
            logger.warning("Failed to convert timestamp, using current time",
                         timestamp=timestamp,
                         timestamp_type=type(timestamp).__name__,
                         error=str(e))
            return datetime.utcnow()
    
    def _map_role_to_sender(self, role: str) -> TranscriptSender:
        """Map Pipecat message role to TranscriptSender enum."""
        if role == "user":
            return TranscriptSender.CANDIDATE
        elif role == "assistant":
            return TranscriptSender.INTERVIEWER
        else:
            # Default to CANDIDATE for unknown roles
            logger.warning("Unknown message role, defaulting to CANDIDATE", role=role)
            return TranscriptSender.CANDIDATE
    
    def _detect_code_content(self, content: str) -> bool:
        """
        Simple heuristic to detect if message contains code.
        TODO: Implement more sophisticated code detection.
        """
        code_indicators = [
            '```',  # Code blocks
            'def ',  # Python functions
            'function ',  # JavaScript functions
            'class ',  # Class definitions
            'import ',  # Import statements
            'from ',  # Python imports
            '{',  # Curly braces
            ';',  # Semicolons
            '++',  # Increment operators
            '--',  # Decrement operators
        ]
        
        return any(indicator in content for indicator in code_indicators)
    
    def user(self, **kwargs):
        """
        Get or create the user transcript processor instance.
        
        This processor handles TranscriptionFrames from STT services.
        
        Args:
            **kwargs: Arguments passed to the UserTranscriptProcessor constructor
            
        Returns:
            UserTranscriptProcessor instance for processing user messages
        """
        user_processor = self.transcript_processor.user(**kwargs)
        user_processor._role = "user"  # Add role identifier for event handling
        logger.debug("User transcript processor created", session_id=self.session_id)
        return user_processor
    
    def assistant(self, **kwargs):
        """
        Get or create the assistant transcript processor instance.
        
        This processor handles TTSTextFrames from TTS services and aggregates 
        them into complete utterances.
        
        Args:
            **kwargs: Arguments passed to the AssistantTranscriptProcessor constructor
            
        Returns:
            AssistantTranscriptProcessor instance for processing assistant messages
        """
        assistant_processor = self.transcript_processor.assistant(**kwargs)
        assistant_processor._role = "assistant"  # Add role identifier for event handling
        logger.debug("Assistant transcript processor created", session_id=self.session_id)
        return assistant_processor
    
    def add_subscriber(self, event_type: str, subscriber_callback):
        """
        Add a custom subscriber for transcript events.
        
        Args:
            event_type: Type of event to subscribe to
            subscriber_callback: Async function to handle events
        """
        self.event_bus.subscribe(event_type, subscriber_callback)
        logger.info("Custom subscriber added",
                   event_type=event_type,
                   callback=subscriber_callback.__name__,
                   session_id=self.session_id)
    
    def remove_subscriber(self, event_type: str, subscriber_callback) -> bool:
        """
        Remove a subscriber for transcript events.
        
        Args:
            event_type: Type of event to unsubscribe from
            subscriber_callback: Callback function to remove
            
        Returns:
            True if subscriber was removed, False if not found
        """
        result = self.event_bus.unsubscribe(event_type, subscriber_callback)
        if result:
            logger.info("Custom subscriber removed",
                       event_type=event_type,
                       callback=subscriber_callback.__name__,
                       session_id=self.session_id)
        return result
    
    async def publish_session_started(self):
        """Publish session started event."""
        event = TranscriptEvent(
            candidate_interview_id=self.candidate_interview_id,
            sender=TranscriptSender.INTERVIEWER,
            message="Interview session started",
            timestamp=datetime.utcnow(),
            session_id=self.session_id
        )
        await self.event_bus.publish("session_started", event)
    
    async def publish_session_ended(self):
        """Publish session ended event."""
        event = TranscriptEvent(
            candidate_interview_id=self.candidate_interview_id,
            sender=TranscriptSender.INTERVIEWER,
            message="Interview session ended",
            timestamp=datetime.utcnow(),
            session_id=self.session_id
        )
        await self.event_bus.publish("session_ended", event)
    
    def get_session_info(self):
        """Get information about the current transcript session."""
        return {
            "session_id": self.session_id,
            "candidate_interview_id": self.candidate_interview_id,
            "interview_context": bool(self.interview_context),
            "database_storage_enabled": self.db_subscriber is not None,
            "event_bus_status": self.event_bus.get_status(),
            "db_subscriber_status": self.db_subscriber.get_status() if self.db_subscriber else None,
            "processors_created": {
                "user": hasattr(self.transcript_processor, '_user_processor'),
                "assistant": hasattr(self.transcript_processor, '_assistant_processor')
            }
        }
