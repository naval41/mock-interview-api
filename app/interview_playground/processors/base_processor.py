"""
Base Processor class that extends FrameProcessor for direct pipeline integration.
"""

from abc import ABC
from pipecat.frames.frames import Frame, StartFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frame_processor import FrameProcessor


class BaseProcessor(FrameProcessor, ABC):
    """Base class for processor implementations.
    
    Extends FrameProcessor directly for pipeline integration while providing
    proper StartFrame handling and a simple interface for message processing.
    """
    
    def __init__(self, name: str = None, **kwargs):
        """Initialize the BaseProcessor with a name.
        
        Args:
            name: Name for the processor (optional)
            **kwargs: Additional arguments to pass to FrameProcessor
        """
        super().__init__(name=name or self.__class__.__name__, **kwargs)
        
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames with proper StartFrame handling.
        
        This method ensures that the parent FrameProcessor's process_frame
        is called first to handle StartFrame validation and other system frames,
        then calls the child's custom processing logic.
        
        Args:
            frame: Frame to process
            direction: Direction of frame processing
        """
        # CRITICAL: Call parent's process_frame first for StartFrame validation
        await super().process_frame(frame, direction)
        
        # Custom processing logic can be implemented in child classes
        await self.process_custom_frame(frame, direction)
        
    async def process_custom_frame(self, frame: Frame, direction: FrameDirection):
        """Override this method in child classes for custom frame processing.
        
        This method is called after the parent FrameProcessor has validated
        the frame sequence (including StartFrame handling).
        
        Args:
            frame: Frame to process
            direction: Direction of frame processing
        """
        # Default implementation just passes the frame through
        await self.push_frame(frame, direction)
