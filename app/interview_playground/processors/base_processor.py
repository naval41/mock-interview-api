"""
Base Processor class that provides a simple interface for getting FrameProcessor instances.
"""

from abc import ABC, abstractmethod
from pipecat.processors.frame_processor import FrameProcessor


class BaseProcessor(ABC):
    """Base class for processor implementations.
    
    Provides a simple interface to get FrameProcessor instances
    for different processor types.
    """
    
    @abstractmethod
    def setup_processor(self) -> FrameProcessor:
        """Setup the FrameProcessor instance for this processor.
        
        Returns:
            FrameProcessor instance configured for this processor
        """
        pass
        
    @abstractmethod
    async def process_message(self, message: str) -> dict:
        """Process a message and return the result.
        
        Args:
            message: Message to process
            
        Returns:
            Dictionary containing processed result
        """
        pass
