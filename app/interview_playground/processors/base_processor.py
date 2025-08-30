"""
Base Processor class that extends FrameProcessor for direct pipeline integration.
"""

from abc import ABC, abstractmethod
from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frame_processor import FrameProcessor


class BaseProcessor(FrameProcessor, ABC):
    """Base class for processor implementations.
    
    Extends FrameProcessor directly for pipeline integration while providing
    a simple interface for message processing.
    """
    
    def __init__(self, name: str = None, **kwargs):
        """Initialize the BaseProcessor with a name.
        
        Args:
            name: Name for the processor (optional)
            **kwargs: Additional arguments to pass to FrameProcessor
        """
        super().__init__(name=name or self.__class__.__name__, **kwargs)
        
    @abstractmethod
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process a message and return the result.
        
        Args:
            message: Message to process
            
        Returns:
            Dictionary containing processed result
        """
        pass
