"""
Google LLM implementation that extends BaseLLM.
"""

from pipecat.processors.frame_processor import FrameProcessor
from app.interview_playground.llm.base_llm import BaseLLM
from pipecat.services.google.llm import GoogleLLMService

class GoogleLLM(BaseLLM):
    """Google LLM implementation."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        """Initialize Google LLM.
        
        Args:
            api_key: Google API key
            model: Model name for generation
        """
        self.api_key = api_key
        self.model = model
        
    def setup_processor(self) -> FrameProcessor:
        """Setup the Google LLM FrameProcessor instance.
        
        Returns:
            FrameProcessor configured for Google LLM
        """
        from pipecat.processors.frame_processor import FrameProcessor
        
        processor = GoogleLLMService(
            model=self.model,
            api_key=self.api_key,
        )

        return processor
