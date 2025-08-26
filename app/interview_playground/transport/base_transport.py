"""
Base Transport class that provides a simple interface for getting FrameProcessor instances.
"""

from abc import ABC, abstractmethod
from pipecat.processors.frame_processor import FrameProcessor


class BaseTransport(ABC):
    """Base class for transport implementations.
    
    Provides a simple interface to get FrameProcessor instances
    for different transport providers.
    """
    
    @abstractmethod
    def setup_processor(self) -> FrameProcessor:
        """Setup the FrameProcessor instance for this transport.
        
        Returns:
            FrameProcessor instance configured for this transport
        """
        pass