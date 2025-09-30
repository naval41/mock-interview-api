"""
Internal event bus for transcript processing.
Provides pub-sub mechanism for decoupling transcript capture from storage.
"""

import asyncio
from typing import Dict, List, Callable, Any
import structlog
from app.entities.transcript_event import TranscriptEvent

logger = structlog.get_logger()


class TranscriptEventBus:
    """
    Internal event bus for transcript processing.
    
    Provides asynchronous pub-sub mechanism to decouple transcript capture
    from storage and other processing operations.
    """
    
    def __init__(self):
        """Initialize event bus with empty subscriber registry."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_count = 0
        
    def subscribe(self, event_type: str, callback: Callable[[TranscriptEvent], Any]) -> None:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Type of event to subscribe to (e.g., "transcript_created")
            callback: Async function to call when event occurs
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
            
        self._subscribers[event_type].append(callback)
        
        logger.debug("Event subscriber registered",
                    event_type=event_type,
                    callback=callback.__name__,
                    total_subscribers=len(self._subscribers[event_type]))
    
    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """
        Unsubscribe from events of a specific type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Callback function to remove
            
        Returns:
            True if callback was found and removed, False otherwise
        """
        if event_type not in self._subscribers:
            return False
            
        try:
            self._subscribers[event_type].remove(callback)
            logger.debug("Event subscriber removed",
                        event_type=event_type,
                        callback=callback.__name__)
            return True
        except ValueError:
            return False
    
    async def publish(self, event_type: str, event: TranscriptEvent) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event being published
            event: Event data to publish
        """
        self._event_count += 1
        
        if event_type not in self._subscribers:
            logger.debug("No subscribers for event type",
                        event_type=event_type,
                        event_data=str(event))
            return
        
        subscribers = self._subscribers[event_type]
        logger.debug("Publishing event",
                    event_type=event_type,
                    event_data=str(event),
                    subscriber_count=len(subscribers),
                    total_events=self._event_count)
        
        # Execute all subscribers concurrently
        tasks = []
        for callback in subscribers:
            try:
                # Handle both sync and async callbacks
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    # Wrap sync callback in async
                    tasks.append(asyncio.create_task(asyncio.to_thread(callback, event)))
            except Exception as e:
                logger.error("Error creating task for subscriber",
                           event_type=event_type,
                           callback=callback.__name__,
                           error=str(e))
        
        # Wait for all subscribers to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any exceptions from subscribers
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    callback_name = subscribers[i].__name__
                    logger.error("Subscriber failed to process event",
                               event_type=event_type,
                               callback=callback_name,
                               error=str(result),
                               event_data=str(event))
    
    def get_subscriber_count(self, event_type: str) -> int:
        """Get number of subscribers for a specific event type."""
        return len(self._subscribers.get(event_type, []))
    
    def get_total_events(self) -> int:
        """Get total number of events published."""
        return self._event_count
    
    def get_status(self) -> Dict[str, Any]:
        """Get event bus status for debugging."""
        return {
            "total_event_types": len(self._subscribers),
            "total_subscribers": sum(len(subs) for subs in self._subscribers.values()),
            "total_events_published": self._event_count,
            "event_types": {
                event_type: len(subscribers) 
                for event_type, subscribers in self._subscribers.items()
            }
        }
