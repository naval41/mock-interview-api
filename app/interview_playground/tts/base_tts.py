"""
Base TTS class that provides a simple interface for getting FrameProcessor instances.
"""

from abc import ABC, abstractmethod
from pipecat.processors.frame_processor import FrameProcessor


class BaseTTS(ABC):
    """Base class for TTS implementations.
    
    Provides a simple interface to get FrameProcessor instances
    for different TTS providers.
    """
    
    @abstractmethod
    def setup_processor(self) -> FrameProcessor:
        """Setup the FrameProcessor instance for this TTS provider.
        
        Returns:
            FrameProcessor instance configured for this TTS provider
        """
        pass
