"""
Base STT class that provides a simple interface for getting FrameProcessor instances.
"""

from abc import ABC, abstractmethod
from pipecat.processors.frame_processor import FrameProcessor


class BaseSTT(ABC):
    """Base class for STT implementations.
    
    Provides a simple interface to get FrameProcessor instances
    for different STT providers.
    """
    
    @abstractmethod
    def setup_processor(self) -> FrameProcessor:
        """Setup the FrameProcessor instance for this STT provider.
        
        Returns:
            FrameProcessor instance configured for this STT provider
        """
        pass
