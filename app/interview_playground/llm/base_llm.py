"""
Base LLM class that provides a simple interface for getting FrameProcessor instances.
"""

from abc import ABC, abstractmethod
from pipecat.processors.frame_processor import FrameProcessor


class BaseLLM(ABC):
    """Base class for LLM implementations.
    
    Provides a simple interface to get FrameProcessor instances
    for different LLM providers.
    """
    
    @abstractmethod
    def setup_processor(self) -> FrameProcessor:
        """Setup the FrameProcessor instance for this LLM provider.
        
        Returns:
            FrameProcessor instance configured for this LLM provider
        """
        pass
